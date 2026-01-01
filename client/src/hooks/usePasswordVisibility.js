import { useCallback, useMemo, useState } from 'react';

/**
 * Hook genérico para alternar a visibilidade de campos de senha.
 * Apenas gerencia estado e rótulo de acessibilidade; a UI fica a cargo do componente.
 */
export function usePasswordVisibility({ initiallyVisible = false, label = 'senha' } = {}) {
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

