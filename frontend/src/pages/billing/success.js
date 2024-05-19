// pages/billing/success.js

import { useRouter } from "next/router";
import { useEffect } from "react";

import Layout from "layout";
import Page from "components/Page";
import MainCard from "components/MainCard";
import { Typography } from "@mui/material";

const SuccessPage = () => {
  const router = useRouter();
  const { session_id } = router.query; // Retrieve the session ID from the query parameters

  useEffect(() => {
    // Here, you might want to verify the payment was successful by calling your backend with the session_id
    // For now, we'll just log it to the console
    console.log("Stripe session ID:", session_id);

    // Implement any redirection or state update logic here
  }, [session_id]);

  return (
    <Page title="Payment Successful">
      <MainCard content={false}>
        <h2>Payment Successful</h2>
        <Typography variant="subtitle1">
          Your subscription has been activated. Thank you for your payment!
        </Typography>
      </MainCard>
    </Page>
  );
};

SuccessPage.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default SuccessPage;
