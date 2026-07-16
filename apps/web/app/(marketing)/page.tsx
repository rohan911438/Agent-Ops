import Link from "next/link";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";

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
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-sm font-semibold tracking-tight">AgentOps Cloud</span>
          <nav className="flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#pricing" className="hover:text-foreground">
              Pricing
            </a>
            <Link href="/health-scan/new">
              <Button size="sm">Start Health Scan</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-4xl px-6 py-28 text-center">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            The Enterprise Control Plane for AI Agents.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            Run a Health Scan and get an Executive Report in minutes: how many agents you have,
            where money is being wasted, where risk is highest, and the top 5 highest-ROI actions
            to take next.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link href="/health-scan/new">
              <Button size="lg">Start Health Scan</Button>
            </Link>
            <a href="#how-it-works">
              <Button size="lg" variant="outline">
                See how it works
              </Button>
            </a>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="border-t border-border py-24">
          <div className="mx-auto max-w-6xl px-6">
            <h2 className="text-center text-2xl font-semibold tracking-tight">
              What AI agents do I have? What are they doing? What risks exist?
            </h2>
            <div className="mt-12 grid gap-6 sm:grid-cols-3">
              {features.map((f) => (
                <Card key={f.title}>
                  <CardHeader>
                    <CardTitle className="text-base text-foreground">{f.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {f.description}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="border-t border-border py-24">
          <div className="mx-auto max-w-6xl px-6">
            <h2 className="text-center text-2xl font-semibold tracking-tight">How it works</h2>
            <div className="mt-12 grid gap-8 sm:grid-cols-3">
              {steps.map((s) => (
                <div key={s.step}>
                  <div className="text-sm font-mono text-muted-foreground">{s.step}</div>
                  <h3 className="mt-2 font-medium">{s.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{s.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Architecture */}
        <section id="architecture" className="border-t border-border py-24">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Built for enterprise scale</h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm text-muted-foreground">
              A modular control plane — org-scoped from day one, with a connector architecture
              ready for GitHub, LangGraph, CrewAI, MCP, Kubernetes, and every major cloud, and an
              SDK for automatic agent discovery on the roadmap.
            </p>
          </div>
        </section>

        {/* Pricing placeholder */}
        <section id="pricing" className="border-t border-border py-24">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Pricing</h2>
            <p className="mt-4 text-sm text-muted-foreground">
              Enterprise pricing — talk to us once you&apos;ve seen your agent inventory.
            </p>
            <div className="mt-8 flex justify-center">
              <Card className="w-full max-w-sm">
                <CardHeader>
                  <CardTitle className="text-foreground">Enterprise</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Custom pricing based on agents under management. Contact sales.
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border py-24">
          <div className="mx-auto max-w-2xl px-6 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">
              See what&apos;s running across your company.
            </h2>
            <div className="mt-6">
              <Link href="/health-scan/new">
                <Button size="lg">Start Health Scan</Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-10">
        <div className="mx-auto max-w-6xl px-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} AgentOps Cloud.
        </div>
      </footer>
    </>
  );
}
