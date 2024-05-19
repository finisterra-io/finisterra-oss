import PropTypes from "prop-types";
import NextLink from "next/link";
import { useCallback, useEffect, useMemo, useState, Fragment } from "react";
import { alpha, useTheme } from "@mui/material/styles";
import {
  Button,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  useMediaQuery,
  Typography,
} from "@mui/material";

import { useSnackbar } from "notistack";

import {
  useFilters,
  useExpanded,
  useGlobalFilter,
  useRowSelect,
  useSortBy,
  useTable,
  usePagination,
} from "react-table";

import Layout from "layout";
import Page from "components/Page";
import MainCard from "components/MainCard";
import ScrollX from "components/ScrollX";
import IconButton from "components/@extended/IconButton";
import { HeaderSort, TablePagination } from "components/third-party/ReactTable";

import AWSAccountPreview from "sections/aws/AWSAccountPreview";

import { renderFilterTypes, GlobalFilter } from "utils/react-table";

import { dispatch, useSelector } from "store";

import { getAWSAccounts } from "store/reducers/aws-account";

// assets
import { PlusOutlined } from "@ant-design/icons";

import { FaEdit } from "react-icons/fa";

import { loadStripe } from "@stripe/stripe-js";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY);

// ==============================|| REACT TABLE ||============================== //

function ReactTable({ columns, data, renderRowSubComponent, permissionToAdd }) {
  const theme = useTheme();
  const matchDownSM = useMediaQuery(theme.breakpoints.down("sm"));
  // const memorizedData = useMemo(() => data, [reload]);

  const filterTypes = useMemo(() => renderFilterTypes, []);

  const sortBy = { id: "name", desc: false };

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    setHiddenColumns,
    visibleColumns,
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

  const [loading, setLoading] = useState(false);

  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (matchDownSM) {
      setHiddenColumns([
        "id",
        "accountId",
        "roleArn",
        "sessionDuration",
        "status",
      ]);
    } else {
      setHiddenColumns(["id"]);
    }
  }, [matchDownSM]);

  const handleStartSubscription = async () => {
    setLoading(true);

    try {
      const stripe = await stripePromise;
      // Call to backend API to start the subscription
      const response = await fetch("/api/billing/start-subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const { sessionId } = await response.json();
        // Redirect to Stripe Checkout
        const { error } = await stripe.redirectToCheckout({ sessionId });
        if (error) throw new Error(error.message);
      } else {
        throw new Error("Failed to start subscription");
      }
    } catch (error) {
      enqueueSnackbar(error.message, { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

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
          <Stack
            direction={matchDownSM ? "column" : "row"}
            alignItems="center"
            spacing={1}
          >
            <NextLink href="/aws/aws-account-wizard" passHref>
              <Button
                variant="contained"
                startIcon={<PlusOutlined />}
                size="small"
                disabled={!permissionToAdd}
              >
                Add AWS Account
              </Button>
            </NextLink>
            {!permissionToAdd && (
              <Button
                variant="contained"
                color="primary"
                onClick={handleStartSubscription}
                disabled={loading}
              >
                Start Subscription
              </Button>
            )}
          </Stack>
        </Stack>
        <Table {...getTableProps()}>
          <TableHead>
            {headerGroups.map((headerGroup, index) => (
              <TableRow
                {...headerGroup.getHeaderGroupProps()}
                key={index}
                sx={{ "& > th:first-of-type": { width: "58px" } }}
              >
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
                  {row.isExpanded &&
                    renderRowSubComponent({
                      row,
                      rowProps,
                      visibleColumns,
                      expanded,
                    })}
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
  getHeaderProps: PropTypes.func,
  handleAdd: PropTypes.func,
  renderRowSubComponent: PropTypes.any,
  permissionToAdd: PropTypes.bool,
};

// ==============================|| AWS - LIST ||============================== //

const ActionsCell = (row, theme) => {
  return (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="center"
      spacing={0}
    >
      <NextLink href={`/aws/${row.original.id}/details`} passHref>
        <Tooltip title="View Details">
          <IconButton color="primary">
            <FaEdit />
          </IconButton>
        </Tooltip>
      </NextLink>
    </Stack>
  );
};

ActionsCell.propTypes = {
  row: PropTypes.object,
  theme: PropTypes.array,
};

const AWSAccountListPage = () => {
  const { accounts } = useSelector((state) => state.awsAccount);

  const selectEnabledAccounts = (state) => state.awsAccount.enabledAccounts;

  const enabledAccounts = useSelector(selectEnabledAccounts);

  const theme = useTheme();

  const [AWSAccount, setAWSAccount] = useState(null);
  const [add, setAdd] = useState(false);
  const [reload, setReload] = useState(Date.now());
  const [rememo, setRememo] = useState(false);
  const [permissionToAdd, setPermissionToAdd] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      await dispatch(getAWSAccounts());
      setRememo(!rememo);
    };

    const getUsageAndSubscriptionStatus = async () => {
      try {
        const subscriptionResponse = await fetch(
          "/api/billing/subscription-status"
        );
        const subscriptionData = await subscriptionResponse.json();
        if (subscriptionData.usage < 1) {
          setPermissionToAdd(true);
        } else {
          if (subscriptionData.hasActiveSubscription) {
            setPermissionToAdd(true);
          } else {
            setPermissionToAdd(false);
          }
        }
      } catch (error) {
        dispatch(usage.actions.hasError(error));
      }
    };

    getUsageAndSubscriptionStatus();

    fetchData();
  }, [dispatch, reload]);

  const memorizedData = useMemo(
    () => ({ accounts, timestamp: Date.now() }),
    [rememo]
  );

  const handleAdd = () => {
    setAdd(!add);
    if (AWSAccount && !add) setAWSAccount(null);
    setReload(Date.now());
  };

  const columns = useMemo(
    () => [
      {
        Header: "Name",
        accessor: "name",
      },
      {
        Header: "Account ID",
        accessor: "awsAccountId",
      },
      {
        Header: "Region",
        accessor: "region",
      },
      {
        Header: "Role ARN",
        accessor: "roleArn",
      },
      {
        Header: "Status",
        accessor: "enabled",
        Cell: ({ row }) => (
          <Typography>
            {row.original.enabled ? "Enabled" : "Disabled"}
          </Typography>
        ),
      },
      {
        accessor: "id",
        Cell: () => null,
      },
      {
        Header: "Actions",
        className: "cell-center",
        disableSortBy: true,
        Cell: ({ row }) => ActionsCell(row, theme),
      },
    ],
    [theme]
  );

  const renderRowSubComponent = useCallback(
    ({ row }) => <AWSAccountPreview awsAccount={accounts[Number(row.id)]} />,
    [accounts]
  );

  return (
    <Page title="AWS Accounts List">
      <MainCard content={false}>
        <ScrollX>
          <ReactTable
            columns={columns}
            data={memorizedData.accounts}
            handleAdd={handleAdd}
            renderRowSubComponent={renderRowSubComponent}
            reload={reload}
            permissionToAdd={permissionToAdd}
          />
        </ScrollX>
      </MainCard>
    </Page>
  );
};

AWSAccountListPage.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default AWSAccountListPage;
