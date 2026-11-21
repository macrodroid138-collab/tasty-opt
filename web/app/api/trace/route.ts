import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const day = request.nextUrl.searchParams.get("day") || "2024-12-18";
  const trader = request.nextUrl.searchParams.get("trader") || "sigma-carry";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
    return NextResponse.json({ error: "Use a YYYY-MM-DD session." }, { status: 400 });
  }
  if (trader !== "sigma-carry" && trader !== "sigma-clip") {
    return NextResponse.json({ error: "Unknown trader." }, { status: 400 });
  }
  const file = path.join(process.cwd(), "data", "traces", trader, `${day}.json`);
  try {
    const body = await readFile(file, "utf8");
    return NextResponse.json(JSON.parse(body));
  } catch {
    return NextResponse.json({ error: `${day} is not one of the sessions loaded on the desk.` }, { status: 404 });
  }
}
