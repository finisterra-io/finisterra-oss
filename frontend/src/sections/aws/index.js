import { useState } from "react";


import { useRouter } from "next/router";

// material-ui
import {  Step, Stepper, StepLabel } from "@mui/material";

// project imports
import AddAWSAccount from "sections/aws/AddAWSAccount";
import AddGithubAccount from "sections/github/AddGithubAccount";
import AddAWSAccountProgress from "sections/aws/AddAWSAccountProgress";
import MainCard from "components/MainCard";

// step options
const steps = [
  "Select Git Repository",
  "Connect AWS Account",
];

const getStepContent = (
  state,
  step,
  handleNext,
  handleBack,
  awsAccount,
  setAWSAccount,
) => {
  switch (step) {
    case 0:
      return (
        <AddGithubAccount
          handleNext={handleNext}
          awsAccount={awsAccount}
          setAWSAccount={setAWSAccount}
          handleBack={handleBack}
          state={state}
        />
      );
    case 1:
      return (
        <AddAWSAccount
          handleNext={handleNext}
          awsAccount={awsAccount}
          setAWSAccount={setAWSAccount}
          handleBack={handleBack}
        />
      );
    default:
      throw new Error("Unknown step");
  }
};

// ==============================|| FORMS WIZARD - VALIDATION ||============================== //

const AWSAccountWizard = ({ state }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [AWSAccount, setAWSAccount] = useState(null);

  const handleNext = () => {
    setActiveStep(activeStep + 1);
  };

  const handleBack = () => {
    setActiveStep(activeStep - 1);
  };

  return (
    <MainCard title="New AWS Account">
      <Stepper activeStep={activeStep} sx={{ pt: 3, pb: 5 }}>
        {steps.map((label, index) => {
          const labelProps = {};

          return (
            <Step key={label}>
              <StepLabel {...labelProps}>{label}</StepLabel>
            </Step>
          );
        })}
      </Stepper>
      <>
        {activeStep === steps.length ? (
          <AddAWSAccountProgress awsAccount={AWSAccount} />
        ) : (
          <>
            {getStepContent(
              state,
              activeStep,
              handleNext,
              handleBack,
              AWSAccount,
              setAWSAccount,
            )}
            
          </>
        )}
      </>
    </MainCard>
  );
};

export default AWSAccountWizard;
