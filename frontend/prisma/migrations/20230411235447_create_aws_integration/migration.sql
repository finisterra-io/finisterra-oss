-- CreateTable
CREATE TABLE "Tag" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,

    CONSTRAINT "Tag_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AwsAccountTag" (
    "awsAccountId" INTEGER NOT NULL,
    "tagId" INTEGER NOT NULL,

    CONSTRAINT "AwsAccountTag_pkey" PRIMARY KEY ("awsAccountId","tagId")
);

-- CreateIndex
CREATE UNIQUE INDEX "Tag_name_key" ON "Tag"("name");

-- AddForeignKey
ALTER TABLE "AwsAccountTag" ADD CONSTRAINT "AwsAccountTag_awsAccountId_fkey" FOREIGN KEY ("awsAccountId") REFERENCES "AwsAccount"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AwsAccountTag" ADD CONSTRAINT "AwsAccountTag_tagId_fkey" FOREIGN KEY ("tagId") REFERENCES "Tag"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
