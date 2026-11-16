<script>
  let profile = null;
  let username = "admin";
  let password = "123456";
  let loginError = "";
  let trials = [];
  let detail = null;
  let formError = "";
  let busy = false;

  try {
    profile = JSON.parse(localStorage.getItem("germ.profile") || "null");
  } catch {
    profile = null;
  }

  async function request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = localStorage.getItem("germ.token") || "";
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "请求没有完成");
    return data;
  }

  async function refresh(prefer) {
    trials = await request("/api/trials");
    const target = prefer || detail?.trial.id || trials[0]?.id;
    if (target) detail = await request(`/api/trials/${target}`);
  }

  async function submitLogin() {
    loginError = "";
    try {
      const data = await request("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      localStorage.setItem("germ.token", data.access_token);
      profile = { username: data.username, role: data.role, title: data.title };
      localStorage.setItem("germ.profile", JSON.stringify(profile));
      await refresh();
    } catch (error) {
      loginError = error.message;
    }
  }

  async function publishCurrent() {
    if (!detail) return;
    busy = true;
    formError = "";
    try {
      detail = await request(`/api/trials/${detail.trial.id}/publish`, { method: "POST" });
      trials = await request("/api/trials");
    } catch (error) {
      formError = error.message;
    } finally {
      busy = false;
    }
  }

  function logout() {
    localStorage.removeItem("germ.token");
    localStorage.removeItem("germ.profile");
    profile = null;
    detail = null;
  }

  if (profile) {
    refresh().catch(() => logout());
  }
</script>

{#if !profile}
  <main class="paper gate">
    <p class="kicker">种子检验室</p>
    <h1>发芽口径核算台</h1>
    <p>现行口径：分母是播种粒数减去霉粒数，分子是发芽粒数。霉变种子不计入可计种子。</p>
    <form on:submit|preventDefault={submitLogin}>
      <label>用户<input bind:value={username} /></label>
      <label>口令<input type="password" bind:value={password} /></label>
      <button>打开记录</button>
      {#if loginError}<p class="warn">{loginError}</p>{/if}
    </form>
  </main>
{:else}
  <header class="bar">
    <div>
      <p class="kicker">口径核算</p>
      <h1>发芽口径核算台</h1>
    </div>
    <div class="who">
      <span>{profile.title} {profile.username}</span>
      <button class="quiet" on:click={logout}>离开</button>
    </div>
  </header>
  <main class="desk">
    <aside>
      {#each trials as trial}
        <button class:on={detail && detail.trial.id === trial.id} on:click={() => request(`/api/trials/${trial.id}`).then((data) => (detail = data))}>
          <strong>{trial.lot_code}</strong>
          <em>{trial.crop_name}</em>
          <span>{trial.status}</span>
        </button>
      {/each}
    </aside>
    {#if detail}
      <article class="paper">
        <div class="head">
          <h2>{detail.trial.lot_code} · {detail.trial.crop_name}</h2>
          <button disabled={profile.role !== "writer" || busy} on:click={publishCurrent}>按现行口径出数</button>
        </div>
        <p>{detail.trial.status}</p>
        <p class="rule">现行口径的分母是播种粒数减去霉粒数。旧口径把霉粒留在分母里，出过的数字不会被抹掉。</p>
        {#if profile.role !== "writer"}<p>见证员只能核对，不能出数。</p>{/if}
        {#if formError}<p class="warn">{formError}</p>{/if}
        <table>
          <thead>
            <tr><th>床</th><th>播种</th><th>发芽</th><th>霉粒</th></tr>
          </thead>
          <tbody>
            {#each detail.beds as bed}
              <tr>
                <td>{bed.bed_no}</td>
                <td>{bed.sown}</td>
                <td>{bed.sprouted}</td>
                <td>{bed.moldy}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        <h3>出数记录</h3>
        {#each detail.publications as row}
          <section class="edition" class:old={!row.current}>
            <strong>{row.current ? "现行口径" : "旧口径"} {row.rate_label}</strong>
            <span>分母 {row.tested} · 剔除霉粒 {row.excluded_mold} · 发芽 {row.sprouted}</span>
            <em>{row.note} · {row.published_by} · {row.published_at}</em>
          </section>
        {/each}
      </article>
    {/if}
  </main>
{/if}

<style>
  .bar, .desk, .gate { width: min(1100px, calc(100% - 32px)); margin: 0 auto; }
  .bar { display: flex; justify-content: space-between; align-items: end; padding: 28px 0 8px; }
  .kicker { margin: 0 0 4px; letter-spacing: 0.16em; color: #b4332a; font-size: 13px; }
  h1, h2, h3 { font-weight: 560; margin: 0; }
  .who { display: flex; gap: 12px; align-items: center; }
  .desk { display: grid; grid-template-columns: 240px 1fr; gap: 18px; padding-bottom: 40px; }
  .paper { background: rgba(255, 250, 242, 0.94); padding: 22px; box-shadow: 0 10px 30px rgba(44, 36, 22, 0.05); }
  .gate { margin-top: 40px; width: min(520px, calc(100% - 32px)); }
  form, aside { display: grid; gap: 10px; }
  label { display: grid; gap: 6px; }
  input { border: 0; border-bottom: 1px solid #b4332a; background: transparent; padding: 8px 0; color: #2c2416; }
  button { background: #b4332a; color: #fffaf2; border: 0; padding: 8px 12px; }
  .quiet { background: transparent; color: #2c2416; border-bottom: 1px solid #2c2416; }
  aside button { text-align: left; background: transparent; color: #2c2416; border-bottom: 1px solid rgba(180, 51, 42, 0.35); display: grid; }
  aside button.on { background: #fffaf2; }
  aside em, .edition em { font-style: normal; color: #7a6a55; }
  .head { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
  .rule { color: #7a6a55; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
  th, td { text-align: left; padding: 8px 4px; border-bottom: 1px solid rgba(180, 51, 42, 0.25); }
  .edition { display: grid; gap: 4px; padding: 10px 0; border-top: 1px dashed rgba(180, 51, 42, 0.4); }
  .old strong { color: #7a6a55; }
  .warn { color: #b4332a; }
  @media (max-width: 800px) {
    .desk { grid-template-columns: 1fr; }
  }
</style>
