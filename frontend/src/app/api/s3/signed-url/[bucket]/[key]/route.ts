import { s3Client } from "@/server/aws";
import {
  GetObjectCommand,
  type GetObjectCommandInput,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const contextSchema = z.object({
  key: z.string(),
  bucket: z.string(),
});

export async function GET(
  req: NextRequest,
  context: { params: { key: string; bucket: string } },
) {

  const result = contextSchema.safeParse(context.params);

  if (!result.success) {
    return NextResponse.json(
      { error: "Missin required parameters: key, bucket" },
      { status: 400 },
    );
  }

  const s3Params: GetObjectCommandInput = {
    Bucket: result.data.bucket,
    Key: result.data.key,
  };

  try {
    const command = new GetObjectCommand(s3Params);
    const signedURL = await getSignedUrl(s3Client, command, {
      expiresIn: 3600,
    });
    return NextResponse.json({ signedURL }, { status: 200 });
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      { error: "Failed to generate signed URL" },
      { status: 500 },
    );
  }
}
