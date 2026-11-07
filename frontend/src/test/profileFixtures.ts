import type { ProfileDetailData } from '@/types/profile'

export function profileFixture(): ProfileDetailData {
  return {
    profile: { grade: '大一', major: '计算机科学与技术', foundation: '注册时的基础说明',
      learning_goals: ['旧目标'], interests: ['旧兴趣'], difficulty_preference: 'progressive',
      courses: ['程序设计'], read_books: [], career_direction: null },
    effective_profile: { grade: '大二', major: '软件工程', foundation: 'Python: none',
      learning_goals: ['完成课程项目'], interests: [], difficulty_preference: 'beginner',
      abilities: { python: { topic: 'Python', level: 'none', basis: 'self_report' },
        java: { topic: 'Java', level: 'advanced', basis: 'self_report' },
        database: { topic: '数据库', level: 'unknown', basis: 'self_report' } },
      sources: { 'topic:python': { memory_id: 'active-python', source: 'conversation', source_message_id: 'message-1',
        is_user_edited: false, updated_at: '2026-11-07T08:00:00Z', confidence: 0.95, evidence: '我没学过 Python' } } },
    memories: [
      { id: 'active-python', category: 'foundation', key: 'topic:python', value_json: { topic: 'Python', level: 'none' },
        source: 'conversation', source_message_id: 'message-1', confidence: 0.95, is_active: true, is_user_edited: false,
        created_at: '2026-11-07T08:00:00Z', updated_at: '2026-11-07T08:00:00Z' },
      { id: 'old-python', category: 'foundation', key: 'topic:Python', value_json: { topic: 'Python', level: 'advanced' },
        source: 'conversation', source_message_id: 'message-0', confidence: 0.9, is_active: false, is_user_edited: false,
        created_at: '2026-11-06T08:00:00Z', updated_at: '2026-11-07T08:00:00Z' }
    ]
  }
}
