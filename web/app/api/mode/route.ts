import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const trader = request.nextUrl.searchParams.get("trader") === "sigma-clip" ? "sigma-clip" : "sigma-carry";
  const mode = request.nextUrl.searchParams.get("mode") === "live" ? "live" : "demo";
  if (mode === "demo") {
    return NextResponse.json({
      trader,
      mode,
      connected: true,
      account: null,
      message: "Demo mode. Orders stay on this machine and are not sent to Tastytrade.",
    });
  }
  const missing = ["TASTY_CLIENT_SECRET", "TASTY_REFRESH_TOKEN", "TASTY_ACCOUNT_NUMBER"].filter((name) => !process.env[name]);
  if (missing.length) {
    return NextResponse.json({
      trader,
      mode,
      connected: false,
      account: null,
      message: `Live mode needs ${missing.join(", ")}. No order will be sent until they are set.`,
    });
  }
  return NextResponse.json({
    trader,
    mode,
    connected: false,
      account: null,
      message: "Credentials are present. The live program signs in from its own process, and it sends real orders.",
  });
}
