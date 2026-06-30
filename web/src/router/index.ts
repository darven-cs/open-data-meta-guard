import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import ChatView from '@/views/ChatView.vue'

// Phase 0 占位（5 个 View），Phase 1-5 各自替换为真实页面
import MetaCollectView from '@/views/MetaCollectView.vue'
import MetaEvaluateView from '@/views/MetaEvaluateView.vue'
import DataCollectView from '@/views/DataCollectView.vue'
import DataQualityView from '@/views/DataQualityView.vue'
import KnowledgeGraphView from '@/views/KnowledgeGraphView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { layout: 'admin', title: '总览' },
  },
  {
    path: '/chat',
    name: 'chat',
    // /chat 不加 meta.layout，保持 ChatLayout 原全屏行为
    component: ChatView,
    meta: { title: '数据小D' },
  },
  {
    path: '/meta-collect',
    name: 'meta-collect',
    component: MetaCollectView,
    meta: { layout: 'admin', title: '元数据采集' },
  },
  {
    path: '/meta-evaluate',
    name: 'meta-evaluate',
    component: MetaEvaluateView,
    meta: { layout: 'admin', title: '元数据评估' },
  },
  {
    path: '/data-collect',
    name: 'data-collect',
    component: DataCollectView,
    meta: { layout: 'admin', title: '数据采集' },
  },
  {
    path: '/data-quality',
    name: 'data-quality',
    component: DataQualityView,
    meta: { layout: 'admin', title: '数据质量评估' },
  },
  {
    path: '/kg',
    name: 'kg',
    component: KnowledgeGraphView,
    meta: { layout: 'admin', title: '知识图谱' },
  },
  // 兜底：任何未匹配路径回首页
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

// 路由切换时更新 document.title（浏览器标签友好）
const BRAND = '开放数据元数据治理 · v2.0'
router.afterEach((to) => {
  const t = to.meta?.title as string | undefined
  document.title = t && t !== BRAND ? `${t} · ${BRAND}` : BRAND
})

export default router
