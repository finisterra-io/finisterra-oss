import { Grid } from "@mui/material";

import { v4 as uuidv4 } from "uuid";
import jwt from "jsonwebtoken";
import { authOptions } from "pages/api/auth/[...nextauth]";
import { getServerSession } from "next-auth/next";

// project imports
import Layout from "layout";
import Page from "components/Page";
import AWSAccountWizard from "sections/aws/";

// ==============================|| FORMS WIZARD ||============================== //

const NewAWSAccountWizard = ({ state }) => (
  <Page title="New AWS Account">
    <Grid container spacing={2.5} justifyContent="center">
      <Grid item xs={12} md={6} lg={7}>
        <AWSAccountWizard state={state} />
      </Grid>
    </Grid>
  </Page>
);

NewAWSAccountWizard.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default NewAWSAccountWizard;

export async function getServerSideProps(context) {
  const { req, res } = context;
  const session = await getServerSession(req, res, authOptions);
  const state = jwt.sign(
    { uuid: uuidv4(), organizationId: session.organizationId },
    process.env.JWT_SECRET
  );

  return {
    props: {
      state,
    },
  };
}
