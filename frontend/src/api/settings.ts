// 设置相关接口封装

export interface SettingsData {
  translate_provider: string
  deepl_api_key: string
  google_api_key: string
  openai_api_key: string
  openai_base_url: string
  openai_model: string
  word_pick_hotkey: string
  word_pick_lang: string
  region_poll_interval: number
  exit_on_close: boolean
}

export async function getSettings(): Promise<SettingsData> {
  const res = await fetch('/api/settings')
  if (!res.ok) throw new Error(`读取设置失败：${res.status}`)
  return (await res.json()) as SettingsData
}

export async function saveSettings(patch: Partial<SettingsData>): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return (await res.json()) as { ok: boolean; error?: string }
}

export async function testSettings(patch: Partial<SettingsData>): Promise<{ ok: boolean; error?: string; sample?: string }> {
  const res = await fetch('/api/settings/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return (await res.json()) as { ok: boolean; error?: string; sample?: string }
}
