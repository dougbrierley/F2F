"use client"

import { useCallback, useState } from "react";
import { set, z } from "zod";

type DownloadFileResponse = {
  name: string;
  url: string;
};

export const SignedURLsSchema = z.object({
  signedURLs: z.string().array()
});

export const SignedURLSchema = z.object({
  signedURL: z.string()
});


const fetchFile = async ({ key, bucket }: { key: string; bucket: string }) => {
  const res = await fetch(`/api/s3/signed-url/${bucket}/${key}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = SignedURLSchema.safeParse(await res.json());

  if (!result.success) {
    throw new Error("Failed to fetch signed URL");
  }

  const { signedURL } = result.data;

  return {
    name: key,
    url: signedURL,
  };
};

export const useFetchFromS3 = ({
  onURLComplete,
  onURLError,
}: {
  onURLComplete?: (res?: DownloadFileResponse) => void;
  onURLError?: (err: unknown) => void;
}) => {
  const [isFetching, setIsFetching] = useState(false);

  const fetchFromS3 = useCallback(
    async (key: string, bucket: string) => {
      setIsFetching(true);
      try {
        const res = await fetchFile({
          key,
          bucket,
        });
        onURLComplete && onURLComplete(res);
      } catch (e) {
        console.log(e);
        onURLError && onURLError(e);
      } finally {
        setIsFetching(false);
      }
    },
    [setIsFetching, onURLComplete, onURLError],
  );

  return { fetchFromS3, isFetching } as const;
};
function fetchWithProgress(
  url: string,
  opts: {
    headers?: Headers;
    method?: string;
    file?: File;
  } = {},
  onProgress?: (this: XMLHttpRequest, progress: ProgressEvent) => void,
  onUploadBegin?: (this: XMLHttpRequest, progress: ProgressEvent) => void,
) {
  return new Promise<XMLHttpRequest>((res, rej) => {
    const xhr = new XMLHttpRequest();
    xhr.open(opts.method ?? "get", url);
    opts.headers &&
      Object.keys(opts.headers).forEach(
        (h) =>
          opts.headers && xhr.setRequestHeader(h, opts.headers.get(h) ?? ""),
      );
    xhr.onload = (e) => {
      res(e.target as XMLHttpRequest);
    };

    xhr.onerror = rej;
    if (xhr.upload && onProgress) xhr.upload.onprogress = onProgress;
    if (xhr.upload && onUploadBegin) xhr.upload.onloadstart = onUploadBegin;
    xhr.send(opts.file);
  });
}

type UploadFileResponse = {
  name: string;
  size: number;
};

const uploadFiles = async ({
  onUploadProgress,
  onUploadBegin,
  files,
}: {
  onUploadProgress?: (progress: number[]) => void;
  onUploadBegin?: () => void;
  files: File[];
}) => {

  const res = await fetch("/api/s3/signed-url", {
    method: "POST",
    body: JSON.stringify({
      files: files.map((file) => ({
        fileName: file.name,
        fileType: file.type,
      })),
    }),
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = SignedURLsSchema.safeParse(await res.json());

  if (!result.success) {
    throw new Error("Failed to fetch signed URL");
  }

  const { signedURLs } = result.data;

  let progress_array: number[] = Array(files.length).fill(0);

  const uploads = await Promise.all(
    files.map(async (file, i) => {
      const signedURL = signedURLs[i];
      const fileName = file.name;

      const upload = await fetchWithProgress(
        signedURL,
        {
          method: "PUT",
          file,
        },
        (progressEvent) => {
          if (!onUploadProgress) return;
          if (!progressEvent.lengthComputable) return;
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );
          progress_array[i]= progress;
          onUploadProgress(progress_array);
        },
        () => {
          if (!onUploadBegin) return;
          onUploadBegin();
        },
      );

      if (upload.status > 299 || upload.status < 200) {
        console.log(upload);
        throw new Error("Failed to upload");
      }

      return {
        name: fileName,
        size: file.size,
      };
    }),
  );

  return uploads
};

export const useUploadToS3 = ({
  onUploadProgress,
  onUploadBegin,
  onClientUploadComplete,
  onUploadError,
}: {
  onUploadProgress: (progress: number[]) => void;
  onUploadBegin?: () => void;
  onClientUploadComplete?: (res?: UploadFileResponse[]) => void;
  onUploadError?: (err: unknown) => void;
}) => {
  const [isUploading, setIsUploading] = useState(false);

  const uploadToS3 = useCallback(
    async (files: File[]) => {
      setIsUploading(true);
      onUploadProgress([]);
      try {
        const res = await uploadFiles({
          onUploadProgress,
          onUploadBegin,
          files,
        });
        onClientUploadComplete && onClientUploadComplete(res);
      } catch (e) {
        console.log(e);
        onUploadError && onUploadError(e);
      } finally {
        setIsUploading(false);
        onUploadProgress([]);
      }
    },
    [
      setIsUploading,
      onUploadProgress,
      onUploadBegin,
      onClientUploadComplete,
      onUploadError,
    ],
  );

  return { uploadToS3, isUploading } as const;
};
