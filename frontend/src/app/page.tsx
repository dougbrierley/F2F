"use client"

import Upload from "@/components/upload/upload";
import { useUploadToS3 } from "@/lib/s3";
import Image from "next/image";
import { useState } from "react";


export default function Home() {
  const [progress, setProgress] = useState(0);



  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <div className="flex flex-col items-center justify-between">
          <h1 className="text-4xl font-bold text-center">
            Welcome to Farm To Fork
          </h1>
          <p className="text-center">
            Oxford University Farm To Fork
          </p>
          <Upload />
        </div>
      </div>
    </main>
  );
}
