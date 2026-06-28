import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource-variable/fraunces'
import '@fontsource-variable/inter-tight'
import '@fontsource-variable/jetbrains-mono'
import './styles/base.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())  // 注册 pinia 状态管理
app.use(router)         // 注册 vue-router（总览 / 元数据采集 / 元数据评估 / 数据采集 / 数据质量评估 / 数据小D）
app.mount('#app')
