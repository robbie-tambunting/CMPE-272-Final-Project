import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PROJECT_ROOT } from "@/lib/spawn-stream";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const file = searchParams.get("file");
  
  if (!file) {
    return NextResponse.json({ exists: false });
  }

  const filePath = path.resolve(PROJECT_ROOT, file);
  const exists = fs.existsSync(filePath);
  
  return NextResponse.json({ exists });
}
