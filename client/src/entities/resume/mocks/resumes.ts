import type { Resume } from '../model/types';

export const resumesMock: Resume[] = [
  {
    id: 'r1',
    name: 'Desenvolvedor Full Stack',
    updatedAt: '2024-01-14T10:00:00.000Z',
    status: 'complete',
    score: 85,
    tags: ['React', 'Node.js', 'TypeScript', 'PostgreSQL', 'Docker'],
  },
  {
    id: 'r2',
    name: 'Product Manager',
    updatedAt: '2024-01-09T16:30:00.000Z',
    status: 'analyzing',
    score: 72,
    tags: ['Scrum', 'Kanban', 'Data Analysis', 'Discovery', 'Roadmap'],
  },
  {
    id: 'r3',
    name: 'UX Designer',
    updatedAt: '2024-01-04T09:10:00.000Z',
    status: 'draft',
    score: 0,
    tags: ['Figma', 'Adobe XD', 'User Research', 'Design System'],
  },
  {
    id: 'r4',
    name: 'Analista de Dados',
    updatedAt: '2024-01-18T12:05:00.000Z',
    status: 'complete',
    score: 90,
    tags: ['SQL', 'Python', 'Power BI', 'ETL', 'Statistics'],
  },
  {
    id: 'r5',
    name: 'Engenheiro de Software (Backend)',
    updatedAt: '2024-01-20T20:00:00.000Z',
    status: 'draft',
    score: 40,
    tags: ['Django', 'REST', 'Redis', 'AWS', 'Testing'],
  },
];
