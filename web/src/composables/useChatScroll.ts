import { ref, watch, onScopeDispose, type Ref } from 'vue'
import { useScroll, useResizeObserver } from '@vueuse/core'
import { useChatStore } from '@/stores/chat'
import { storeToRefs } from 'pinia'

interface UseChatScrollOptions {
  /** 距底部多少 px 内算"到达底部"（useScroll offset.bottom） */
  bottomOffset?: number
  /** FAB 显示的距离阈值：未粘底且离底超过此值才显示按钮（避免小抖动频繁显隐） */
  fabThreshold?: number
}

/**
 * 智能粘底自动滚动 composable —— 对齐 ChatGPT / Claude.ai 行为
 *
 * 三条核心规则：
 *   1. 粘底态：内容增长（SSE token / markdown rAF / 代码块 highlight / 图片加载）→ 自动滚到底
 *   2. 用户向上滚 → 立刻解除粘底，停止跟随
 *   3. 用户滚回底部 → 恢复粘底
 *
 * 触发源（不污染数据层）：
 *   - useResizeObserver(contentRef) —— 抓 rAF 异步渲染的高度变化（不用 watch messages，更解耦）
 *   - useScroll(scrollerRef) —— arrivedState.bottom / directions.top / y
 *
 * @param scrollerRef  滚动容器（MessageList 根 div，CSS overflow-y: auto 在它身上）
 * @param contentRef   内容容器（包住 v-for messages 的内层 div，ResizeObserver 监听它）
 */
export function useChatScroll(
  scrollerRef: Ref<HTMLElement | null>,
  contentRef: Ref<HTMLElement | null>,
  options: UseChatScrollOptions = {},
) {
  const { bottomOffset = 32, fabThreshold = 80 } = options

  // 默认粘底：首次挂载 + 发消息后都希望滚到底
  const isSticky = ref(true)
  // FAB 显隐（派生：未粘底 + 离底距离 > 阈值）
  const showJumpToBottom = ref(false)

  const { y, arrivedState, directions } = useScroll(scrollerRef, {
    offset: { bottom: bottomOffset },
  })

  let rafId: number | null = null

  /**
   * 强制滚到底部。
   * - smooth=true：FAB 点击用，平滑动画
   * - smooth=false：流式跟随用，瞬时跳（避免动画追尾导致追不上 token）
   *
   * 任何调用方意图都是"回到底部"，所以同步把 isSticky 置 true。
   */
  function scrollToBottom(smooth = false) {
    isSticky.value = true
    const el = scrollerRef.value
    if (!el) return
    el.scrollTo({
      top: el.scrollHeight,
      left: 0,
      behavior: smooth ? 'smooth' : 'auto',
    })
  }

  /**
   * rAF 单帧 latch 调度的内部跟随滚动。
   * 高频 SSE token append 触发多次 ResizeObserver，本函数把它们合并到一帧内只滚一次。
   * 仅在粘底态执行；非粘底时仅刷新 FAB 显隐。
   */
  function scheduleScrollToBottom() {
    updateShowFab()
    if (!isSticky.value) return
    if (rafId !== null) return  // 单帧 latch：已排队 → 跳过
    rafId = requestAnimationFrame(() => {
      rafId = null
      const el = scrollerRef.value
      if (!el) return
      // 不走 scrollToBottom(smooth=false)，避免重复写 isSticky=true 触发 watch 抖动
      el.scrollTo({ top: el.scrollHeight, left: 0, behavior: 'auto' })
    })
  }

  /** 重算 FAB 显隐：未粘底 + 离底距离 > 阈值 */
  function updateShowFab() {
    const el = scrollerRef.value
    if (!el) {
      showJumpToBottom.value = false
      return
    }
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight
    showJumpToBottom.value = !isSticky.value && distance > fabThreshold
  }

  // 1. 内容尺寸变化（markdown rAF 渲染 / 代码块 highlight / 图片加载 / SSE token append）
  useResizeObserver(contentRef, () => {
    scheduleScrollToBottom()
  })

  // 2. 用户主动向上滚 → 立刻解除粘底（directions.top 在用户滚动方向转为向上时为 true）
  watch(
    () => directions.top,
    (up) => {
      if (up) {
        isSticky.value = false
        updateShowFab()
      }
    },
  )

  // 3. 滚回底部（在 bottomOffset 阈值内）→ 恢复粘底
  watch(
    () => arrivedState.bottom,
    (atBottom) => {
      if (atBottom) {
        isSticky.value = true
        updateShowFab()
      }
    },
  )

  // 4. 滚动位置变化 → 重算 FAB（用户持续向上滚时 distance 增大，FAB 该出现）
  watch(y, updateShowFab)

  // 5. 切会话 → 重置粘底 + 滚到底部（rAF 等新 messages 渲染完再滚）
  const store = useChatStore()
  const { currentId } = storeToRefs(store)
  watch(currentId, () => {
    isSticky.value = true
    showJumpToBottom.value = false
    requestAnimationFrame(() => {
      const el = scrollerRef.value
      if (!el) return
      el.scrollTo({ top: el.scrollHeight, left: 0, behavior: 'auto' })
    })
  })

  // 卸载时清理 rAF，避免内存泄漏 + 对已卸载组件赋值
  onScopeDispose(() => {
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
  })

  return {
    isSticky,
    showJumpToBottom,
    scrollToBottom,
  }
}
