import PropTypes from "prop-types";

import { useEffect, useMemo, useState, Fragment } from "react";
// material-ui
import { alpha, useTheme } from "@mui/material/styles";
import {
  Switch,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  useMediaQuery,
} from "@mui/material";

// third-party
import {
  useFilters,
  useExpanded,
  useGlobalFilter,
  useRowSelect,
  useSortBy,
  useTable,
  usePagination,
} from "react-table";

// project import
import Page from "components/Page";
import MainCard from "components/MainCard";
import ScrollX from "components/ScrollX";
import { HeaderSort, TablePagination } from "components/third-party/ReactTable";

import { renderFilterTypes, GlobalFilter } from "utils/react-table";

import { dispatch, useSelector } from "store";

import { getWorkspaces } from "store/reducers/workspace";

// ==============================|| REACT TABLE ||============================== //

function ReactTable({ columns, data }) {
  const theme = useTheme();
  const matchDownSM = useMediaQuery(theme.breakpoints.down("sm"));

  const filterTypes = useMemo(() => renderFilterTypes, []);

  const sortBy = { id: "name", desc: false };

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    setHiddenColumns,
    rows,
    page,
    gotoPage,
    setPageSize,
    state: { globalFilter, pageIndex, pageSize, expanded },
    preGlobalFilteredRows,
    setGlobalFilter,
  } = useTable(
    {
      columns,
      data,
      filterTypes,
      initialState: {
        pageIndex: 0,
        pageSize: 10,
        hiddenColumns: [],
        sortBy: [sortBy],
      },
    },
    useGlobalFilter,
    useFilters,
    useSortBy,
    useExpanded,
    usePagination,
    useRowSelect
  );

  useEffect(() => {
    if (matchDownSM) {
      setHiddenColumns(["id", "state", "module", "provider"]);
    } else {
      setHiddenColumns(["id"]);
    }
    // eslint-disable-next-line
  }, [matchDownSM]);

  return (
    <>
      <Stack spacing={3}>
        <Stack
          direction={matchDownSM ? "column" : "row"}
          spacing={1}
          justifyContent="space-between"
          alignItems="center"
          sx={{ p: 3, pb: 0 }}
        >
          <GlobalFilter
            preGlobalFilteredRows={preGlobalFilteredRows}
            globalFilter={globalFilter}
            setGlobalFilter={setGlobalFilter}
            size="small"
          />
        </Stack>
        <Table {...getTableProps()}>
          <TableHead>
            {headerGroups.map((headerGroup, index) => (
              <TableRow {...headerGroup.getHeaderGroupProps()} key={index}>
                {headerGroup.headers.map((column, i) => (
                  <TableCell
                    {...column.getHeaderProps([
                      { className: column.className },
                    ])}
                    key={i}
                  >
                    <HeaderSort column={column} sort />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody {...getTableBodyProps()}>
            {page.map((row, i) => {
              prepareRow(row);
              const rowProps = row.getRowProps();

              return (
                <Fragment key={i}>
                  <TableRow
                    {...row.getRowProps()}
                    onClick={() => {
                      row.toggleRowSelected();
                    }}
                    sx={{
                      cursor: "pointer",
                      bgcolor: row.isSelected
                        ? alpha(theme.palette.primary.lighter, 0.35)
                        : "inherit",
                    }}
                  >
                    {row.cells.map((cell, i) => (
                      <TableCell
                        {...cell.getCellProps([
                          { className: cell.column.className },
                        ])}
                        key={i}
                      >
                        {cell.render("Cell")}
                      </TableCell>
                    ))}
                  </TableRow>
                </Fragment>
              );
            })}
            <TableRow sx={{ "&:hover": { bgcolor: "transparent !important" } }}>
              <TableCell sx={{ p: 2, py: 3 }} colSpan={9}>
                <TablePagination
                  gotoPage={gotoPage}
                  rows={rows}
                  setPageSize={setPageSize}
                  pageSize={pageSize}
                  pageIndex={pageIndex}
                />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Stack>
    </>
  );
}

ReactTable.propTypes = {
  columns: PropTypes.array,
  data: PropTypes.array,
};

// ==============================|| Workspace - LIST ||============================== //

const StatusCell = ({ value, onChange }) => {
  return (
    <Switch
      checked={value}
      onChange={onChange}
      color="primary"
      inputProps={{ "aria-label": "status toggle" }}
    />
  );
};

StatusCell.propTypes = {
  value: PropTypes.bool,
};

const WorkspaceList = ({ awsAccountId }) => {
  const { workspaces } = useSelector((state) => state.workspace);
  const theme = useTheme();

  const [Workspace, setWorkspace] = useState(null);
  const [add, setAdd] = useState(false);
  const [reload, setReload] = useState(Date.now());
  const [rememo, setRememo] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      await dispatch(getWorkspaces(awsAccountId));
      setRememo(!rememo);
    };

    fetchData();
  }, [dispatch, reload]);

  const memorizedData = useMemo(
    () => ({ workspaces, timestamp: Date.now() }),
    [rememo]
  );

  const handleAdd = () => {
    setAdd(!add);
    if (Workspace && !add) setWorkspace(null);
    setReload(Date.now());
  };

  const handleToggle = async (id, enabled) => {
    try {
      const response = await fetch(`/api/workspace/workspace`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id,
          enabled,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update workspace status");
      }

      setReload(Date.now());
    } catch (error) {
      console.error("Error updating workspace status:", error);
    }
  };

  const columns = useMemo(
    () => [
      {
        Header: "Name",
        accessor: "name",
      },
      {
        Header: "Account Name",
        accessor: (row) => `${row.awsAccount.name}`,
      },
      {
        Header: "Module",
        id: "module",
        accessor: "providerGroup.name",
      },
      {
        Header: "Provider",
        id: "provider",
        accessor: () => `AWS`,
      },
      {
        Header: "Enabled",
        accessor: "enabled",
        Cell: ({ row }) => (
          <Switch
            checked={row.original.enabled}
            onChange={(e) => handleToggle(row.original.id, e.target.checked)}
            color="primary"
            inputProps={{ "aria-label": "status toggle" }}
          />
        ),
      },
      {
        accessor: "id",
        Cell: () => null,
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [theme]
  );

  return (
    <Page title="Workspace Accounts List">
      <MainCard content={false}>
        <ScrollX>
          <ReactTable
            columns={columns}
            data={memorizedData.workspaces}
            handleAdd={handleAdd}
            reload={reload}
          />
        </ScrollX>
      </MainCard>
    </Page>
  );
};

export default WorkspaceList;
