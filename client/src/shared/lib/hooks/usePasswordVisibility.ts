import { useCallback, useMemo, useState } from 'react';

type Params = {
  initiallyVisible?: boolean;
  label?: string;
};

export function usePasswordVisibility(params: Params = {}) {
  const { initiallyVisible = false, label = 'senha' } = params;
  const [isVisible, setIsVisible] = useState(initiallyVisible);

  const toggleVisibility = useCallback(() => {
    setIsVisible((prev) => !prev);
  }, []);

  const inputType = isVisible ? 'text' : 'password';

  const ariaLabel = useMemo(
    () => (isVisible ? `Ocultar ${label}` : `Mostrar ${label}`),
    [isVisible, label]
  );

  return { isVisible, inputType, toggleVisibility, ariaLabel };
}


