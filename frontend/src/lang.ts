// DeepL 支持的语言列表（DeepL 语言代码 + 中文名）

export interface LangOption {
  label: string
  value: string
}

export const DEEPL_LANGS: LangOption[] = [
  { label: '中文', value: 'ZH' },
  { label: '英语', value: 'EN' },
  { label: '日语', value: 'JA' },
  { label: '韩语', value: 'KO' },
  { label: '法语', value: 'FR' },
  { label: '德语', value: 'DE' },
  { label: '西班牙语', value: 'ES' },
  { label: '葡萄牙语', value: 'PT' },
  { label: '意大利语', value: 'IT' },
  { label: '俄语', value: 'RU' },
  { label: '荷兰语', value: 'NL' },
  { label: '波兰语', value: 'PL' },
  { label: '瑞典语', value: 'SV' },
  { label: '丹麦语', value: 'DA' },
  { label: '芬兰语', value: 'FI' },
  { label: '挪威语', value: 'NB' },
  { label: '捷克语', value: 'CS' },
  { label: '斯洛伐克语', value: 'SK' },
  { label: '希腊语', value: 'EL' },
  { label: '匈牙利语', value: 'HU' },
  { label: '罗马尼亚语', value: 'RO' },
  { label: '保加利亚语', value: 'BG' },
  { label: '立陶宛语', value: 'LT' },
  { label: '拉脱维亚语', value: 'LV' },
  { label: '爱沙尼亚语', value: 'ET' },
  { label: '斯洛文尼亚语', value: 'SL' },
  { label: '克罗地亚语', value: 'HR' },
  { label: '乌克兰语', value: 'UK' },
  { label: '土耳其语', value: 'TR' },
  { label: '印尼语', value: 'ID' },
  { label: '阿拉伯语', value: 'AR' },
  { label: '越南语', value: 'VI' },
  { label: '泰语', value: 'TH' },
]

// 原文语言选择：默认"自动"（不传 source_lang，由 DeepL 自动识别），也可指定单一语言
export const SOURCE_LANG_OPTIONS: LangOption[] = [{ label: '自动', value: 'auto' }, ...DEEPL_LANGS]

// 译文目标语言，默认中文
export const TARGET_LANG_OPTIONS: LangOption[] = [...DEEPL_LANGS]
