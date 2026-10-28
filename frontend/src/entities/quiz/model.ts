import { z } from 'zod';
export const choices = ['A', 'B', 'C', 'D'] as const;
export const choiceSchema = z.enum(choices);
const id = z.number().int().positive();
const count = z.number().int().nonnegative();
const options = z.object({ A: z.string(), B: z.string(), C: z.string(), D: z.string() });
export const quizWriteSchema = z.object({
  question_count: z.number().int().min(1).max(100),
  passing_score: z.number().int().min(1).max(100),
  time_limit_seconds: z.number().int().min(60).max(7200),
  enabled: z.boolean(),
});
export const questionWriteSchema = z.object({
  lesson_id: id,
  prompt: z.string().trim().min(1).max(10000),
  options: z.object(
    Object.fromEntries(
      choices.map((choice) => [choice, z.string().trim().min(1).max(2000)]),
    ) as Record<Choice, z.ZodString>,
  ),
  correct_option: choiceSchema,
  explanation: z.string().trim().min(1).max(10000),
  is_active: z.boolean(),
});
const configSchema = quizWriteSchema.extend({ id, module_id: id, revision: id });
const lesson = z.object({ id, module_id: id, title: z.string(), position: id });
const question = questionWriteSchema.extend({ id, module_id: id, lesson_title: z.string() });
export const bankSchema = z.object({
  module_id: id,
  title: z.string(),
  course_status: z.enum(['draft', 'published', 'archived']),
  lessons: z.array(lesson),
  config: configSchema.nullable(),
  active_questions: count,
  items: z.array(question),
  total: count,
  limit: id,
  offset: count,
});
const publicQuestion = z.object({
  question_id: id,
  lesson_id: id,
  lesson_title: z.string(),
  prompt: z.string(),
  options,
});
const resultSchema = z.object({
  correct_count: count,
  total: id,
  score_percent: count.max(100),
  passed: z.boolean(),
  questions: z.array(
    publicQuestion.extend({
      selected_option: choiceSchema.nullable(),
      correct_option: choiceSchema,
      explanation: z.string(),
      is_correct: z.boolean(),
    }),
  ),
  review_lessons: z.array(
    z.object({ lesson_id: id.nullable(), title: z.string(), wrong_answers: id }),
  ),
});
export const attemptSchema = z.object({
  attempt_id: z.uuid(),
  course_id: id,
  module_id: id.nullable(),
  module_title: z.string(),
  quiz_revision: id,
  passing_score: id.max(100),
  started_at: z.iso.datetime({ offset: true }),
  deadline_at: z.iso.datetime({ offset: true }),
  server_time: z.iso.datetime({ offset: true }),
  status: z.enum(['in_progress', 'submitted', 'expired']),
  questions: z.array(publicQuestion),
  answers: z.record(z.string(), choiceSchema),
  result: resultSchema.nullable(),
});
export const infoSchema = z.object({
  module_id: id,
  available: z.boolean(),
  question_count: id,
  passing_score: id,
  time_limit_seconds: id,
  remaining_today: count,
  daily_limit: id,
  reset_at: z.iso.datetime({ offset: true }),
  timezone: z.string(),
  open_attempt: z.uuid().nullable(),
});
export const historySchema = z.object({
  items: z.array(
    z.object({
      attempt_id: z.uuid(),
      status: z.enum(['in_progress', 'submitted', 'expired']),
      started_at: z.iso.datetime({ offset: true }),
      score_percent: count.nullable(),
      passed: z.boolean().nullable(),
    }),
  ),
  total: count,
  limit: id,
  offset: count,
});
export const progressSchema = z.object({
  course_id: id,
  modules: z.array(
    z.object({
      module_id: id,
      title: z.string(),
      lesson_count: count,
      completed_lessons: count,
      completed_lesson_ids: z.array(id),
      quiz_enabled: z.boolean(),
      quiz_passed: z.boolean(),
      best_score: count.nullable(),
    }),
  ),
  lesson_count: count,
  completed_lessons: count,
  lesson_percent: count.max(100),
  passed_modules: count,
  module_count: count,
  quiz_percent: count.max(100),
  complete: z.boolean(),
});
export type Choice = z.infer<typeof choiceSchema>;
export type QuizWrite = z.infer<typeof quizWriteSchema>;
export type QuestionWrite = z.infer<typeof questionWriteSchema>;
export type Bank = z.infer<typeof bankSchema>;
export type Question = z.infer<typeof question>;
export type Attempt = z.infer<typeof attemptSchema>;
export type QuizInfo = z.infer<typeof infoSchema>;
export type Progress = z.infer<typeof progressSchema>;
