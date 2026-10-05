import { Suspense } from "react";

import { AuthForm } from "@/components/auth/AuthForm";

// Suspense for the same reason as the login page: AuthForm reads
// useSearchParams for `next`, which Next 15 requires a boundary around.
export default function SignupPage() {
  return (
    <Suspense>
      <AuthForm mode="signup" />
    </Suspense>
  );
}
