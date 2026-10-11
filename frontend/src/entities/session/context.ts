import { createContext, useContext, useSyncExternalStore } from 'react';
import type { AccountGateway } from './model/contracts';
import type { SessionManager } from './model/session';
export const AccountContext = createContext<{
  session: SessionManager;
  gateway: AccountGateway;
} | null>(null);
export function useAccount() {
  const context = useContext(AccountContext);
  if (!context) throw new Error('Account provider is missing');
  return context;
}
export function useCurrentUser() {
  const { session } = useAccount();
  return useSyncExternalStore(session.subscribe, session.snapshot, session.snapshot);
}
