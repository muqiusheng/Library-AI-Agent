export type ContentOrientation = 'theory' | 'balanced' | 'practice'

const labels: Record<ContentOrientation, string> = {
  theory: '偏理论', balanced: '理论实践结合', practice: '偏实践'
}

export function contentOrientationLabel(value?: ContentOrientation | null): string {
  return value ? labels[value] : '未标注'
}
