import { cookies } from "next/headers";

import { createClient } from "@/utils/supabase/server";

export default async function Page() {
  const cookieStore = await cookies();
  const supabase = createClient(cookieStore);

  const { data: todos } = await supabase.from("todos").select();

  return (
    <main style={{ padding: "1.5rem" }}>
      <h1>Todos</h1>
      <ul>
        {todos?.map((todo) => (
          <li key={todo.id}>{todo.name}</li>
        ))}
      </ul>
      {!todos?.length && <p>No rows yet. Add a `todos` table or insert sample data.</p>}
    </main>
  );
}
