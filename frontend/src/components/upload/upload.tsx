"use client";

import { useUploadToS3 } from "@/lib/s3";
import { useState } from "react";
import { toast } from "sonner";
import { Input } from "../ui/input";
import { Trash2, UploadCloud } from "lucide-react";
import { Progress } from "../ui/progress";

const MAX_COUNT = 5;

export default function Upload() {
  const [progress, setProgress] = useState<number[]>([]);
  const [currentFiles, setFiles] = useState<File[]>([]);
  const [fileLimit, setFileLimit] = useState(false);

  const { uploadToS3, isUploading } = useUploadToS3({
    onUploadProgress: (progress) => {
      setProgress(progress);
    },
    onUploadBegin: () => {
      console.log("upload begin");
    },
    onClientUploadComplete: (res) => {
      console.log("upload complete", res);
      toast.success("Upload complete");
    },
  });

  const handleUploadFiles = (files: File[]) => {
    const uploaded = [...currentFiles];
    let limitExceeded = false;
    files.some((file) => {
      if (currentFiles.findIndex((f) => f.name === file.name) === -1) {
        uploaded.push(file);
        if (uploaded.length === MAX_COUNT) {
          setFileLimit(true);
          toast.info("Max files reached");
        }
        if (uploaded.length > MAX_COUNT) {
          limitExceeded = true;
          toast.error("You can only upload 5 files at a time");
          setFileLimit(false);
          limitExceeded = true;
          return true;
        }
      }
    });
    if (!limitExceeded) {
      setFiles(uploaded);
    }
  };

  return (
    <div
      id="drop_zone"
      onDrop={() => console.log("You dropped a file")}
      className="p-10 border-2 border-dashed border-neutral-400 rounded-lg flex flex-col items-center gap-2"
    >
      <UploadCloud className="h-16 w-16" />
      <p>
        Drag one or more files to this <i>drop zone</i>.
      </p>
      <label
        htmlFor="files"
        className="hover:cursor-pointer inline-block bg-green-600 text-white px-4 py-2 rounded"
      >
        Choose Files
      </label>
      <Input
        id="files"
        type="file"
        className="hidden"
        required
        multiple
        disabled={isUploading || fileLimit}
        onChange={(e) => {
          if (e.target.files) {
            const chosenFiles = Array.prototype.slice.call(e.target.files);
            handleUploadFiles(chosenFiles);
          }
        }}
      />
      <div className="flex gap-2 flex-col py-2 w-full">
        {currentFiles.map((file, i) => (
          <div key={file.name} className="flex items-center gap-2">
            <Trash2
              className="hover:cursor-pointer h-4 w-4"
              onClick={() => {
                const newFiles = currentFiles.filter(
                  (f) => f.name !== file.name
                );
                setFiles(newFiles);
              }}
            />
            <p>{file.name}</p>
            {progress[i] && <Progress value={progress[i] ?? 0} />}
          </div>
        ))}
      </div>
      <button
        onClick={() => {
          if (!currentFiles) return;
          uploadToS3(currentFiles);
        }}
      >
        Upload
      </button>
    </div>
  );
}
