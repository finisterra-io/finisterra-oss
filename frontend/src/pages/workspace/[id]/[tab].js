import { useState } from "react";

// next
import { useRouter } from "next/router";

// material-ui
import { Box, Tab, Tabs } from "@mui/material";

// project import
import Layout from "layout";
import Page from "components/Page";
import MainCard from "components/MainCard";
import AddWorkspace from "sections/workspace/AddWorkspace";

// assets
import {
  FileTextOutlined,
} from "@ant-design/icons";

// ==============================|| PROFILE - ACCOUNT ||============================== //

const WorkspaceDetails = () => {
  const router = useRouter();
  const { id, tab } = router.query; // Retrieve both the ID and tab from the URL

  const [value, setValue] = useState(tab || "details"); // Default to 'scans' tab if no tab is provided

  const handleChange = (event, newValue) => {
    setValue(newValue);
    router.push(`/workspace/${id}/${newValue}`); // Include both the ID and tab in the URL
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
          </Tabs>
        </Box>
        <Box sx={{ mt: 2.5 }}>
          {tab === "details" && <AddWorkspace workspaceId={router.query.id} />}
        </Box>
      </MainCard>
    </Page>
  );
};

WorkspaceDetails.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default WorkspaceDetails;
