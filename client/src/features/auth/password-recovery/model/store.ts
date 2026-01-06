type PasswordRecoveryState = {
  email: string | null;
  resetToken: string | null;
};

const state: PasswordRecoveryState = {
  email: null,
  resetToken: null,
};

export function setRecoveryEmail(email: string) {
  state.email = email;
}

export function getRecoveryEmail() {
  return state.email;
}

export function setRecoveryResetToken(token: string) {
  state.resetToken = token;
}

export function getRecoveryResetToken() {
  return state.resetToken;
}

export function clearRecovery() {
  state.email = null;
  state.resetToken = null;
}


