export const splitARN = (arn) => {
  if (typeof arn !== "string") {
    // console.error("Invalid ARN:", arn);
    return null; // Or some other default value
  }
  let slashPosition = arn.lastIndexOf("/");
  let result = arn.slice(slashPosition + 1);
  return result;
};
