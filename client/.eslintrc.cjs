module.exports = {
  root: true,
  extends: ['react-app', 'react-app/jest'],
  ignorePatterns: ['**/*.css', '**/*.svg'],
  rules: {
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['@/widgets/*/ui/*', '@/widgets/*/model/*'],
            message: 'Use barrel @/widgets/<slice> instead of deep path (e.g. @/widgets/resume-preview).',
          },
          {
            group: ['@/features/*/api/*'],
            message: 'Use barrel @/features/<slice> instead of deep path (e.g. @/features/resume).',
          },
          {
            group: ['@/entities/*/config/*', '@/entities/*/lib/*', '@/entities/*/model/*', '@/entities/*/ui/*', '@/entities/*/mocks/*'],
            message: 'Use barrel @/entities/<slice> instead of deep path (e.g. @/entities/resume).',
          },
        ],
      },
    ],
    'max-lines': [
      'warn',
      { max: 300, skipBlankLines: true, skipComments: true },
    ],
  },
  overrides: [
    {
      files: ['src/features/resume-builder/model/validation/schemas.ts', 'src/shared/lib/i18n/locales/**/*.ts', 'src/entities/resume/config/themes/**/*.ts'],
      rules: { 'max-lines': 'off' },
    },
  ],
};
