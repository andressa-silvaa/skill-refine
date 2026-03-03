export type VersionHistoryItem = {
  id: string;
  resumeId: string;
  resumeTitle: string;
  version: number;
  isCurrent: boolean;
  score: number;
  createdAt: string;
  changes: string[];
};

export type ResumeFilterOption = {
  id: string;
  title: string;
};
