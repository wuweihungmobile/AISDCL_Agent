// Tremor chartColors [v0.1.0] —— 取自 tremorlabs/tremor（Tremor Raw，copy-paste 元件，Apache-2.0）
// 本專案改動：色票對照表換成 water_green 設計 token（wg-* 別名，見 app/globals.css），不使用 Tailwind 預設調色盤。
// 類別名稱（primary／secondary…）是圖表的語意色；要換色只改這張表。

export type ColorUtility = "bg" | "stroke" | "fill" | "text"

export const chartColors = {
  primary: {
    bg: "bg-wg-primary",
    stroke: "stroke-wg-primary",
    fill: "fill-wg-primary",
    text: "text-wg-primary",
  },
  secondary: {
    bg: "bg-wg-secondary",
    stroke: "stroke-wg-secondary",
    fill: "fill-wg-secondary",
    text: "text-wg-secondary",
  },
  accent: {
    bg: "bg-wg-accent",
    stroke: "stroke-wg-accent",
    fill: "fill-wg-accent",
    text: "text-wg-accent",
  },
  warning: {
    bg: "bg-wg-warning",
    stroke: "stroke-wg-warning",
    fill: "fill-wg-warning",
    text: "text-wg-warning",
  },
  error: {
    bg: "bg-wg-error",
    stroke: "stroke-wg-error",
    fill: "fill-wg-error",
    text: "text-wg-error",
  },
  muted: {
    bg: "bg-wg-muted",
    stroke: "stroke-wg-muted",
    fill: "fill-wg-muted",
    text: "text-wg-muted",
  },
} as const satisfies {
  [color: string]: {
    [key in ColorUtility]: string
  }
}

export type AvailableChartColorsKeys = keyof typeof chartColors

export const AvailableChartColors: AvailableChartColorsKeys[] = Object.keys(
  chartColors,
) as Array<AvailableChartColorsKeys>

export const constructCategoryColors = (
  categories: string[],
  colors: AvailableChartColorsKeys[],
): Map<string, AvailableChartColorsKeys> => {
  const categoryColors = new Map<string, AvailableChartColorsKeys>()
  categories.forEach((category, index) => {
    categoryColors.set(category, colors[index % colors.length])
  })
  return categoryColors
}

export const getColorClassName = (
  color: AvailableChartColorsKeys,
  type: ColorUtility,
): string => {
  const fallbackColor = {
    bg: "bg-wg-muted",
    stroke: "stroke-wg-muted",
    fill: "fill-wg-muted",
    text: "text-wg-muted",
  }
  return chartColors[color]?.[type] ?? fallbackColor[type]
}
