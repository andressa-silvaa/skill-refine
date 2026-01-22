import type { ResumeData } from '../model/types';

const longText =
  'Liderou iniciativas estratégicas com foco em eficiência operacional, governança e resultados mensuráveis, garantindo comunicação clara entre stakeholders e entregas em ciclos curtos.';

const longSummary =
  'Profissional com trajetória sólida em tecnologia e negócios, atuando de ponta a ponta em projetos complexos, com forte foco em resultados, métricas e melhoria contínua. Experiência em liderança de times multidisciplinares, definição de estratégias de produto e entrega de soluções escaláveis em ambientes de alta complexidade. ' +
  'Capacidade de traduzir objetivos de negócio em iniciativas técnicas, alinhando visão, execução e impacto mensurável. ' +
  'Histórico consistente de atuação em contextos internacionais, com comunicação clara, gestão de riscos e priorização baseada em valor.';

const longCompany =
  'Grupo Internacional de Soluções Digitais e Transformação Empresarial LTDA (Unidade Global de Operações)';

const longRole = 'Gerente Sênior de Produto e Estratégia de Plataformas Digitais Multicloud';

const longEmail = 'contato.profissional.muito.longo+curriculo.2026@exemplo-empresa-global.com.br';

const longLink =
  'https://www.linkedin.com/in/profissional-com-nome-muito-longo-e-historico-extenso-estrategia-tecnologia';

export const stressResumeData: ResumeData = {
  themeId: 'classic-one-column',
  targetPosition: longRole,
  contact: {
    fullName: 'Alexandra Fernanda de Albuquerque e Souza Barros',
    email: longEmail,
    phone: '+55 (11) 91234-5678',
    city: 'São Paulo',
    country: 'Brasil',
    linkedin: longLink,
    portfolio: 'https://portfolio.exemplo.com.br/experiencias/projetos/2026/mega-portfolio',
    github: 'https://github.com/exemplo-usuario-com-historico-extenso-e-projetos',
    website: 'https://www.exemplo.com.br/sobre/contato?ref=curriculo-2026',
  },
  summary: longSummary,
  experiences: Array.from({ length: 9 }).map((_, idx) => ({
    id: `exp-stress-${idx}`,
    company: longCompany,
    position: `${longRole} — Escala ${idx + 1}`,
    startDate: `201${idx % 3}-0${(idx % 9) + 1}`,
    endDate: idx % 2 === 0 ? `201${idx % 3}-1${(idx % 2) + 1}` : undefined,
    isCurrent: idx === 0,
    description: [
      longText,
      'Estruturou OKRs trimestrais com foco em crescimento sustentável, garantindo alinhamento com liderança executiva e times de produto.',
      'Reduziu tempo de ciclo em 24% por meio de melhorias contínuas e automações em processos críticos.',
      'Conduziu iniciativas cross-regionais com squads distribuídos e múltiplos fusos horários.',
    ],
  })),
  educations: Array.from({ length: 6 }).map((_, idx) => ({
    id: `edu-stress-${idx}`,
    institution: 'Universidade Federal de Estudos Avançados e Pesquisas Aplicadas',
    course: `Curso Avançado de Gestão Estratégica e Inovação ${idx + 1}`,
    degree: idx % 2 === 0 ? 'Mestrado' : 'MBA',
    startDate: `201${idx}-02`,
    endDate: `201${idx}-12`,
    status: 'completed',
  })),
  skills: Array.from({ length: 28 }).map((_, idx) => ({
    id: `skill-stress-${idx}`,
    name: `Competência Estratégica ${idx + 1}`,
    level: idx % 3 === 0 ? 'expert' : idx % 3 === 1 ? 'advanced' : 'intermediate',
  })),
  languages: [
    { id: 'lang-1', name: 'Português', level: 'native' },
    { id: 'lang-2', name: 'Inglês', level: 'fluent' },
    { id: 'lang-3', name: 'Espanhol', level: 'advanced' },
    { id: 'lang-4', name: 'Francês', level: 'intermediate' },
  ],
};
