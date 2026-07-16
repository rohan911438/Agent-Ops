import { Button, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import { ConnectWalletButton } from "@/components/auth/connect-wallet-button";

const features = [
  {
    title: "Discover every agent",
    description:
      "Automatically surface AI agents running across OpenAI Agents SDK, LangGraph, CrewAI, AutoGen, n8n, MCP servers, and custom code — no matter who built them.",
  },
  {
    title: "Understand ownership & risk",
    description:
      "See who owns each agent, what permissions it holds, and where excess access creates exposure — before it becomes an incident.",
  },
  {
    title: "Optimize cost & performance",
    description:
      "Get explainable, ranked recommendations: merge duplicates, cut spend, retire unused agents, tighten permissions.",
  },
];

const steps = [
  {
    step: "01",
    title: "Connect your infrastructure",
    description: "Point AgentOps at where your agents already run — no rebuild required.",
  },
  {
    step: "02",
    title: "We build the inventory",
    description: "Every agent, its owner, framework, cost, and activity — in one place.",
  },
  {
    step: "03",
    title: "Act on recommendations",
    description: "Ranked, explainable optimizations you can apply with a click.",
  },
];

export default function LandingPage() {
  return (
    <>
      <header className="border-b border-border/80 sticky top-0 bg-background/80 backdrop-blur-md z-50">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-sm font-bold tracking-widest uppercase">AgentOps Cloud</span>
          <nav className="flex items-center gap-6 text-xs uppercase tracking-wider text-muted-foreground">
            <a href="#features" className="hover:text-white transition-colors">
              Features
            </a>
            <a href="#pricing" className="hover:text-white transition-colors">
              Pricing
            </a>
            <ConnectWalletButton size="sm" className="hover:-translate-y-0.5 transition-transform duration-200 font-medium" />
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-4xl px-6 py-32 text-center relative">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-3 py-1 text-xs text-muted-foreground uppercase tracking-wider mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            Control Plane V1.0
          </div>
          <h1 className="text-4xl font-extrabold tracking-tighter sm:text-6xl uppercase leading-none max-w-3xl mx-auto">
            The Enterprise Control Plane for AI Agents.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base text-muted-foreground leading-relaxed">
            Run a Health Scan and get an Executive Report in minutes: how many agents you have,
            where money is being wasted, where risk is highest, and the top 5 highest-ROI actions
            to take next.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <ConnectWalletButton
              size="lg"
              className="hover:-translate-y-0.5 transition-transform duration-200 uppercase tracking-wider text-xs font-semibold px-8"
            />
            <a href="#how-it-works">
              <Button size="lg" variant="outline" className="hover:-translate-y-0.5 transition-transform duration-200 uppercase tracking-wider text-xs font-semibold px-8">
                See how it works
              </Button>
            </a>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="border-t border-border/60 py-28 bg-card/20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">Inventory & Audits</h2>
              <h3 className="text-2xl font-extrabold tracking-tight uppercase sm:text-3xl">
                What AI agents do I have? What are they doing? What risks exist?
              </h3>
            </div>
            <div className="grid gap-6 sm:grid-cols-3">
              {features.map((f) => (
                <Card key={f.title} className="hover:border-zinc-500/40 transition-all duration-300 bg-card/30 backdrop-blur-sm group hover:-translate-y-1">
                  <CardHeader>
                    <CardTitle className="text-sm font-bold uppercase tracking-wider text-foreground group-hover:text-white transition-colors">{f.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm leading-relaxed text-muted-foreground">
                    {f.description}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="border-t border-border/60 py-28">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">Process</h2>
              <h3 className="text-2xl font-extrabold tracking-tight uppercase sm:text-3xl">How it works</h3>
            </div>
            <div className="grid gap-8 sm:grid-cols-3">
              {steps.map((s) => (
                <div key={s.step} className="border border-border/40 p-8 rounded-lg bg-card/10 hover:border-zinc-700 transition-colors">
                  <div className="text-4xl font-extrabold font-mono text-white/10 tracking-tighter">{s.step}</div>
                  <h4 className="mt-4 font-bold text-sm uppercase tracking-wider text-white">{s.title}</h4>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Architecture */}
        <section id="architecture" className="border-t border-border/60 py-28 bg-card/20">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <h2 className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">Architecture</h2>
            <h3 className="text-2xl font-extrabold tracking-tight uppercase sm:text-3xl mb-6">Built for enterprise scale</h3>
            <p className="mx-auto max-w-2xl text-sm leading-relaxed text-muted-foreground">
              A modular control plane — org-scoped from day one, with a connector architecture
              ready for GitHub, LangGraph, CrewAI, MCP, Kubernetes, and every major cloud, and an
              SDK for automatic agent discovery on the roadmap.
            </p>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="border-t border-border/60 py-28">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <h2 className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">Pricing</h2>
            <h3 className="text-2xl font-extrabold tracking-tight uppercase sm:text-3xl mb-4">Enterprise Tiers</h3>
            <p className="text-sm text-muted-foreground mb-12 max-w-md mx-auto">
              Transparent enterprise pricing — talk to us once you&apos;ve seen your agent inventory.
            </p>
            <div className="flex justify-center">
              <Card className="w-full max-w-sm border border-white bg-card hover:shadow-2xl transition-shadow duration-300">
                <CardHeader className="border-b border-border/40 py-6">
                  <CardTitle className="text-sm font-bold uppercase tracking-widest text-foreground">Enterprise</CardTitle>
                </CardHeader>
                <CardContent className="py-8 flex flex-col gap-6">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Custom pricing based on agents under management. Full audit trails, connector access, and compliance scans.
                  </p>
                  <ConnectWalletButton size="lg" className="w-full uppercase tracking-wider text-xs font-bold" />
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border/60 py-28 bg-white text-black">
          <div className="mx-auto max-w-2xl px-6 text-center">
            <h2 className="text-2xl font-extrabold tracking-tighter uppercase sm:text-4xl mb-6">
              See what&apos;s running across your company.
            </h2>
            <div className="mt-8">
              <ConnectWalletButton
                size="lg"
                className="bg-black text-white hover:bg-black/90 uppercase tracking-widest text-xs font-bold px-10 py-6 rounded-none"
              />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/60 py-10 bg-black">
        <div className="mx-auto max-w-6xl px-6 flex justify-between items-center text-xs uppercase tracking-wider text-muted-foreground">
          <span>© {new Date().getFullYear()} AgentOps Cloud.</span>
          <span>Security & Compliance First</span>
        </div>
      </footer>
    </>
  );
}
