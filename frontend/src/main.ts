import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import './style.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(ArcoVue)
// 启用 Arco Design 暗色主题（配合自定义深色科技感样式）
document.body.setAttribute('arco-theme', 'dark')
app.mount('#app')
