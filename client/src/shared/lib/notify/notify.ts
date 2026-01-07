import toast from 'react-hot-toast';

type NotifyOptions = {
  id?: string;
  durationMs?: number;
};

function duration(options?: NotifyOptions) {
  return options?.durationMs;
}

export const notify = {
  success(message: string, options?: NotifyOptions) {
    toast.success(message, { id: options?.id, duration: duration(options) });
  },
  error(message: string, options?: NotifyOptions) {
    toast.error(message, { id: options?.id, duration: duration(options) });
  },
  info(message: string, options?: NotifyOptions) {
    toast(message, { id: options?.id, duration: duration(options) });
  },
  dismiss(id?: string) {
    toast.dismiss(id);
  },
};


