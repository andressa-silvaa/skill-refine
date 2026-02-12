import { useCallback, useReducer } from 'react';

import type { ResumeData, ResumeStatus } from '@/entities/resume';
import type { BuilderStep } from '@/features/resume-builder';

export type ResumesPageState = {
  createOpen: boolean;
  editOpen: boolean;
  editLoading: boolean;
  editResumeId: string | null;
  editData: ResumeData | null;
  editStatus: ResumeStatus | null;
  editLastStep: BuilderStep | null;
  deleteResumeId: string | null;
  isDeleting: boolean;
  duplicateLoadingId: string | null;
  downloadLoadingId: string | null;
  pdfProgress: number;
  isSavingDraft: boolean;
  isSubmitting: boolean;
};

const initialState: ResumesPageState = {
  createOpen: false,
  editOpen: false,
  editLoading: false,
  editResumeId: null,
  editData: null,
  editStatus: null,
  editLastStep: null,
  deleteResumeId: null,
  isDeleting: false,
  duplicateLoadingId: null,
  downloadLoadingId: null,
  pdfProgress: 0,
  isSavingDraft: false,
  isSubmitting: false,
};

export type ResumesPageAction =
  | { type: 'OPEN_CREATE' }
  | { type: 'CLOSE_CREATE' }
  | { type: 'OPEN_EDIT'; payload: { id: string } }
  | { type: 'SET_EDIT_LOADING'; payload: boolean }
  | {
      type: 'SET_EDIT_CONTEXT';
      payload: {
        data: ResumeData | null;
        status: ResumeStatus | null;
        lastStep: BuilderStep | null;
      };
    }
  | { type: 'CLOSE_EDIT' }
  | { type: 'OPEN_DELETE'; payload: { id: string } }
  | { type: 'CLOSE_DELETE' }
  | { type: 'START_DELETING' }
  | { type: 'FINISH_DELETING' }
  | { type: 'START_DUPLICATE'; payload: { id: string } }
  | { type: 'FINISH_DUPLICATE' }
  | { type: 'START_DOWNLOAD'; payload: { id: string } }
  | { type: 'SET_PDF_PROGRESS'; payload: number }
  | { type: 'FINISH_DOWNLOAD' }
  | { type: 'START_SAVING_DRAFT' }
  | { type: 'FINISH_SAVING_DRAFT' }
  | { type: 'START_SUBMITTING' }
  | { type: 'FINISH_SUBMITTING' };

function resumesPageReducer(state: ResumesPageState, action: ResumesPageAction): ResumesPageState {
  switch (action.type) {
    case 'OPEN_CREATE':
      return { ...state, createOpen: true };
    case 'CLOSE_CREATE':
      return { ...state, createOpen: false };
    case 'OPEN_EDIT':
      return {
        ...state,
        editOpen: true,
        editLoading: true,
        editResumeId: action.payload.id,
        editData: null,
        editStatus: null,
        editLastStep: null,
      };
    case 'SET_EDIT_LOADING':
      return { ...state, editLoading: action.payload };
    case 'SET_EDIT_CONTEXT':
      return {
        ...state,
        editData: action.payload.data,
        editStatus: action.payload.status,
        editLastStep: action.payload.lastStep,
        editLoading: false,
      };
    case 'CLOSE_EDIT':
      return {
        ...state,
        editOpen: false,
        editResumeId: null,
        editData: null,
        editStatus: null,
        editLastStep: null,
      };
    case 'OPEN_DELETE':
      return { ...state, deleteResumeId: action.payload.id };
    case 'CLOSE_DELETE':
      return { ...state, deleteResumeId: null };
    case 'START_DELETING':
      return { ...state, isDeleting: true };
    case 'FINISH_DELETING':
      return { ...state, isDeleting: false };
    case 'START_DUPLICATE':
      return { ...state, duplicateLoadingId: action.payload.id };
    case 'FINISH_DUPLICATE':
      return { ...state, duplicateLoadingId: null };
    case 'START_DOWNLOAD':
      return { ...state, downloadLoadingId: action.payload.id, pdfProgress: 0 };
    case 'SET_PDF_PROGRESS':
      return { ...state, pdfProgress: action.payload };
    case 'FINISH_DOWNLOAD':
      return { ...state, downloadLoadingId: null, pdfProgress: 0 };
    case 'START_SAVING_DRAFT':
      return { ...state, isSavingDraft: true };
    case 'FINISH_SAVING_DRAFT':
      return { ...state, isSavingDraft: false };
    case 'START_SUBMITTING':
      return { ...state, isSubmitting: true };
    case 'FINISH_SUBMITTING':
      return { ...state, isSubmitting: false };
    default:
      return state;
  }
}

export function useResumesPageState() {
  const [state, dispatch] = useReducer(resumesPageReducer, initialState);

  const openCreate = useCallback(() => dispatch({ type: 'OPEN_CREATE' }), []);
  const closeCreate = useCallback(() => dispatch({ type: 'CLOSE_CREATE' }), []);

  const openEdit = useCallback((id: string) => dispatch({ type: 'OPEN_EDIT', payload: { id } }), []);
  const setEditLoading = useCallback((loading: boolean) => dispatch({ type: 'SET_EDIT_LOADING', payload: loading }), []);
  const setEditContext = useCallback(
    (ctx: { data: ResumeData | null; status: ResumeStatus | null; lastStep: BuilderStep | null }) =>
      dispatch({ type: 'SET_EDIT_CONTEXT', payload: ctx }),
    []
  );
  const closeEdit = useCallback(() => dispatch({ type: 'CLOSE_EDIT' }), []);

  const openDelete = useCallback((id: string) => dispatch({ type: 'OPEN_DELETE', payload: { id } }), []);
  const closeDelete = useCallback(() => dispatch({ type: 'CLOSE_DELETE' }), []);
  const startDeleting = useCallback(() => dispatch({ type: 'START_DELETING' }), []);
  const finishDeleting = useCallback(() => dispatch({ type: 'FINISH_DELETING' }), []);

  const startDuplicate = useCallback((id: string) => dispatch({ type: 'START_DUPLICATE', payload: { id } }), []);
  const finishDuplicate = useCallback(() => dispatch({ type: 'FINISH_DUPLICATE' }), []);

  const startDownload = useCallback((id: string) => dispatch({ type: 'START_DOWNLOAD', payload: { id } }), []);
  const setPdfProgress = useCallback((n: number) => dispatch({ type: 'SET_PDF_PROGRESS', payload: n }), []);
  const finishDownload = useCallback(() => dispatch({ type: 'FINISH_DOWNLOAD' }), []);

  const startSavingDraft = useCallback(() => dispatch({ type: 'START_SAVING_DRAFT' }), []);
  const finishSavingDraft = useCallback(() => dispatch({ type: 'FINISH_SAVING_DRAFT' }), []);
  const startSubmitting = useCallback(() => dispatch({ type: 'START_SUBMITTING' }), []);
  const finishSubmitting = useCallback(() => dispatch({ type: 'FINISH_SUBMITTING' }), []);

  return {
    state,
    actions: {
      openCreate,
      closeCreate,
      openEdit,
      setEditLoading,
      setEditContext,
      closeEdit,
      openDelete,
      closeDelete,
      startDeleting,
      finishDeleting,
      startDuplicate,
      finishDuplicate,
      startDownload,
      setPdfProgress,
      finishDownload,
      startSavingDraft,
      finishSavingDraft,
      startSubmitting,
      finishSubmitting,
    },
  };
}
