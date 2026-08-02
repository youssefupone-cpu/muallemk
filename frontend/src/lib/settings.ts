/**
 * إعدادات المزوّد/النموذج — تُخزَّن محلياً في المتصفح (localStorage).
 * المفاتيح لا تصل إلى الخادم أبداً إلا عبر الطلب الواحد الذي يستخدمها مباشرة.
 */

export interface ProviderSettings {
  provider: string
  model: string
  baseUrl?: string
  apiKey?: string
}

export const PROVIDERS: { id: string; label: string; hint?: string }[] = [
  { id: 'ollama', label: 'Ollama (محلي)', hint: 'gemma3:1b-it-qat' },
  { id: 'openai', label: 'OpenAI', hint: 'gpt-4o' },
  { id: 'anthropic', label: 'Anthropic', hint: 'claude-sonnet' },
  { id: 'gemini', label: 'Google Gemini', hint: 'gemini-2.5-pro' },
  { id: 'mistral', label: 'Mistral', hint: 'mistral-large' },
  { id: 'groq', label: 'Groq', hint: 'llama-3.3-70b' },
  { id: 'deepseek', label: 'DeepSeek', hint: 'deepseek-chat' },
  { id: 'openrouter', label: 'OpenRouter', hint: 'any-model' },
  { id: 'custom', label: 'مزوّد مخصّص (OpenAI-compat)', hint: 'base_url + مفتاح' },
]

const KEY = 'muallemk.settings'

export const DEFAULT_SETTINGS: ProviderSettings = {
  provider: 'ollama',
  model: 'gemma3:1b-it-qat',
  baseUrl: 'http://localhost:11434',
}

export function loadSettings(): ProviderSettings {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULT_SETTINGS }
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_SETTINGS }
  }
}

export function saveSettings(s: ProviderSettings) {
  localStorage.setItem(KEY, JSON.stringify(s))
}

export function providerLabel(id: string): string {
  return PROVIDERS.find((p) => p.id === id)?.label ?? id
}
