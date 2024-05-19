import { useState } from "react";

// next
import { useRouter } from "next/router";

// material-ui
import { Box, Tab, Tabs } from "@mui/material";

// project import
import Layout from "layout";
import Page from "components/Page";
import MainCard from "components/MainCard";
import UpdateAWSAccount from "sections/aws/UpdateAWSAccount";
import WorkspaceList from "sections/workspace/WorkspaceList";

// assets
import { ContainerOutlined, FileTextOutlined } from "@ant-design/icons";

// ==============================|| PROFILE - ACCOUNT ||============================== //

const WorkspaceDetails = () => {
  const router = useRouter();
  const { id, tab } = router.query; // Retrieve both the ID and tab from the URL

  const [value, setValue] = useState(tab || "details");

  const handleChange = (event, newValue) => {
    setValue(newValue);
    router.push(`/aws/${id}/${newValue}`); // Include both the ID and tab in the URL
  };

  return (
    <Page title="Workspace Details">
      <MainCard border={false} boxShadow>
        <Box sx={{ borderBottom: 1, borderColor: "divider", width: "100%" }}>
          <Tabs
            value={value}
            onChange={handleChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="workspace details tab"
          >
            <Tab
              label="Details"
              icon={<FileTextOutlined />}
              value="details"
              iconPosition="start"
            />

            <Tab
              label="Workspaces"
              icon={<ContainerOutlined />}
              value="workspaces"
              iconPosition="start"
            />
          </Tabs>
        </Box>
        <Box sx={{ mt: 2.5 }}>
          {tab === "details" && (
            <UpdateAWSAccount awsAccountId={router.query.id} />
          )}
          {tab === "workspaces" && (
            <WorkspaceList awsAccountId={router.query.id} />
          )}
        </Box>
      </MainCard>
    </Page>
  );
};

WorkspaceDetails.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default WorkspaceDetails;
