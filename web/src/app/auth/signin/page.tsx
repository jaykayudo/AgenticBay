import { redirect } from "next/navigation";

type AuthSigninPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AuthSigninPage({ searchParams }: AuthSigninPageProps) {
  const params = await searchParams;
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === "string") {
      query.set(key, value);
    }
  });

  redirect(query.size > 0 ? `/login?${query.toString()}` : "/login");
}
