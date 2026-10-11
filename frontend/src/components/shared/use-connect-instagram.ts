"use client";

import { useMutation } from "@tanstack/react-query";
import { instagramApi } from "@/lib/api/manager";
import { ApiError } from "@/lib/api/client";
import { safeNavigationUrl } from "@/lib/safe-url";
import { useToast } from "@/components/ui/toast";

/**
 * POST /instagram/connect, then send the whole browser to `authorize_url`
 * (validated: https, same-origin path, or http on localhost for the mock flow).
 */
export function useConnectInstagram() {
  const toast = useToast();
  return useMutation({
    mutationFn: instagramApi.connect,
    onSuccess: ({ authorize_url }) => {
      const url = safeNavigationUrl(authorize_url);
      if (!url) {
        toast.error("Endereço de autorização inválido.", "Tente novamente em instantes.");
        return;
      }
      window.location.assign(url);
    },
    onError: (e) => {
      toast.error(
        e instanceof ApiError ? e.message : "Não foi possível iniciar a conexão com o Instagram.",
      );
    },
  });
}
