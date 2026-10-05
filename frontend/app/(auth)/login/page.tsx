import { Suspense } from "react";

import { AuthForm } from "@/components/auth/AuthForm";

// Suspense because AuthForm reads useSearchParams for the `next` param, which
// Next 15 requires a boundary around.
export default function LoginPage() {
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
