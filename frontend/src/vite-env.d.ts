/**
 * Type declarations للوحدات الافتراضية (virtual modules).
 * - `virtual:pwa-register/react` يُزوّده vite-plugin-pwa في وقت البناء.
 */
declare module "virtual:pwa-register/react" {
  import type { Dispatch, SetStateAction } from "react";

  export interface UseRegisterSWResult {
    offlineReady: [boolean, Dispatch<SetStateAction<boolean>>];
    needRefresh: [boolean, Dispatch<SetStateAction<boolean>>];
    updateServiceWorker: (reloadPage?: boolean) => Promise<void>;
    registered: boolean;
    registration: ServiceWorkerRegistration | undefined;
  }

  export function useRegisterSW(options?: {
    onRegistered?: (reg: ServiceWorkerRegistration) => void;
    onRegisterError?: (e: Error) => void;
  }): UseRegisterSWResult;
}
