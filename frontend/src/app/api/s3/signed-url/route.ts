import { env } from "@/env";
import { s3Client } from "@/server/aws";
import {
  PutObjectCommand,
  type PutObjectCommandInput,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const ReqSchema = z.object({
  files: z
    .object({
      fileName: z.string(),
      fileType: z.string(),
    })
    .array(),
});

export async function POST(req: NextRequest) {
  const result = ReqSchema.safeParse(await req.json());

  if (!result.success) {
    return NextResponse.json(
      { error: "Missin required parameters: fileName, fileType" },
      { status: 400 }
    );
  }

  try {
    const urls = await Promise.all(
      result.data.files.map(async (file) => {
        const s3Params: PutObjectCommandInput = {
          Bucket: env.AWS_BUCKET_NAME,
          Key: file.fileName,
          ContentType: file.fileType,
        };

        const command = new PutObjectCommand(s3Params);
        const signedURL = await getSignedUrl(s3Client, command, {
          expiresIn: 3600,
        });
        return signedURL;
      })
    );

    return NextResponse.json({ signedURLs: urls }, { status: 200 });
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      { error: "Failed to generate signed URLs" },
      { status: 500 }
    );
  }
}
