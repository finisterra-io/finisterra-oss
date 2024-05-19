import WorkspaceList from "sections/workspace/WorkspaceList";

import Layout from "layout";

const WorkspaceListPage = () => {
  return <WorkspaceList />;
};

WorkspaceListPage.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default WorkspaceListPage;
