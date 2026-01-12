import type { ResumeTemplateId } from './types';

export type ResumeTemplate = {
  id: ResumeTemplateId;
  name: string;
  description: string;
  category: string;
  tags: string[];
  recommended?: boolean;
};

export const resumeTemplates: ResumeTemplate[] = [
  {
    id: 'tech',
    name: 'Desenvolvedor / Tech',
    description: 'Ideal para desenvolvedores, engenheiros de software e profissionais de tecnologia.',
    category: 'Tecnologia',
    tags: ['ATS-friendly', 'Recomendado'],
    recommended: true,
  },
  {
    id: 'business',
    name: 'Produto / Negócios',
    description: 'Foco em resultados, métricas e gestão. Perfeito para PMs e analistas.',
    category: 'Negócios',
    tags: ['ATS-friendly', 'Visual'],
  },
  {
    id: 'design',
    name: 'Design / UX',
    description: 'Destaque para portfólio e projetos. Visual limpo e moderno.',
    category: 'Design',
    tags: ['Visual', 'Recomendado'],
  },
  {
    id: 'marketing',
    name: 'Marketing / Comunicação',
    description: 'Ênfase em campanhas, resultados e comunicação estratégica.',
    category: 'Marketing',
    tags: ['ATS-friendly'],
  },
  {
    id: 'general',
    name: 'Geral / Tradicional',
    description: 'Layout clássico e versátil, adequado para qualquer área.',
    category: 'Geral',
    tags: ['ATS-friendly'],
  },
  {
    id: 'executive',
    name: 'Executivo / Liderança',
    description: 'Elegante e profissional, ideal para cargos de liderança e C-level.',
    category: 'Executivo',
    tags: ['Recomendado'],
  },
  {
    id: 'creative',
    name: 'Criativo / Artes',
    description: 'Para profissionais criativos que querem destacar seu portfólio e projetos visuais.',
    category: 'Criativo',
    tags: ['Visual'],
  },
  {
    id: 'academic',
    name: 'Acadêmico / Pesquisa',
    description: 'Ideal para pesquisadores, professores e profissionais acadêmicos.',
    category: 'Acadêmico',
    tags: ['ATS-friendly'],
  },
  {
    id: 'sales',
    name: 'Vendas / Comercial',
    description: 'Foco em resultados de vendas, metas atingidas e relacionamento com clientes.',
    category: 'Vendas',
    tags: ['ATS-friendly'],
  },
  {
    id: 'healthcare',
    name: 'Saúde / Medicina',
    description: 'Profissional e organizado, perfeito para área da saúde e medicina.',
    category: 'Saúde',
    tags: ['ATS-friendly'],
  },
  {
    id: 'finance',
    name: 'Financeiro / Contábil',
    description: 'Formato tradicional e confiável para profissionais de finanças e contabilidade.',
    category: 'Financeiro',
    tags: ['ATS-friendly'],
  },
  {
    id: 'education',
    name: 'Educação / Ensino',
    description: 'Estruturado e claro, ideal para educadores e profissionais de ensino.',
    category: 'Educação',
    tags: ['ATS-friendly'],
  },
];
