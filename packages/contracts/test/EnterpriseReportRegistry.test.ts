import { expect } from "chai";
import { ethers } from "hardhat";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";
import { EnterpriseReportRegistry } from "../typechain-types";

describe("EnterpriseReportRegistry", () => {
  let registry: EnterpriseReportRegistry;
  let owner: any;
  let submitter: any;
  let stranger: any;

  const REPORT_HASH = ethers.keccak256(ethers.toUtf8Bytes("executive-report-fixture-1"));
  const WORKSPACE_ID = "org_9f2c";
  const VERSION = "phase4.0.0";
  const METADATA_URI = "";

  beforeEach(async () => {
    [owner, submitter, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("EnterpriseReportRegistry");
    registry = (await Factory.deploy(owner.address)) as unknown as EnterpriseReportRegistry;
    await registry.waitForDeployment();
  });

  it("auto-authorizes the initial owner as a submitter", async () => {
    expect(await registry.authorizedSubmitters(owner.address)).to.equal(true);
  });

  it("registers a report hash and emits ReportRegistered", async () => {
    await expect(registry.connect(owner).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI))
      .to.emit(registry, "ReportRegistered")
      .withArgs(REPORT_HASH, WORKSPACE_ID, anyValue, VERSION, owner.address);

    const [exists, proof] = await registry.verifyReport(REPORT_HASH);
    expect(exists).to.equal(true);
    expect(proof.workspaceId).to.equal(WORKSPACE_ID);
    expect(proof.version).to.equal(VERSION);
    expect(proof.submitter).to.equal(owner.address);
    expect(proof.timestamp).to.be.greaterThan(0);
  });

  it("verifyReport reports exists=false for an unregistered hash", async () => {
    const [exists] = await registry.verifyReport(ethers.keccak256(ethers.toUtf8Bytes("never-registered")));
    expect(exists).to.equal(false);
  });

  it("reverts on duplicate registration of the same report hash", async () => {
    await registry.connect(owner).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI);
    await expect(
      registry.connect(owner).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI)
    ).to.be.revertedWithCustomError(registry, "ReportAlreadyRegistered");
  });

  it("rejects registerReport from an unauthorized address", async () => {
    await expect(
      registry.connect(stranger).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI)
    ).to.be.revertedWithCustomError(registry, "NotAuthorized");
  });

  it("owner can authorize a new submitter, who can then register reports", async () => {
    await registry.connect(owner).addAuthorizedSubmitter(submitter.address);
    expect(await registry.authorizedSubmitters(submitter.address)).to.equal(true);

    await expect(registry.connect(submitter).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI)).to.not
      .be.reverted;
  });

  it("owner can revoke a submitter", async () => {
    await registry.connect(owner).addAuthorizedSubmitter(submitter.address);
    await registry.connect(owner).removeAuthorizedSubmitter(submitter.address);
    expect(await registry.authorizedSubmitters(submitter.address)).to.equal(false);

    await expect(
      registry.connect(submitter).registerReport(REPORT_HASH, WORKSPACE_ID, VERSION, METADATA_URI)
    ).to.be.revertedWithCustomError(registry, "NotAuthorized");
  });

  it("rejects addAuthorizedSubmitter / removeAuthorizedSubmitter from a non-owner", async () => {
    await expect(registry.connect(stranger).addAuthorizedSubmitter(stranger.address)).to.be.revertedWithCustomError(
      registry,
      "OwnableUnauthorizedAccount"
    );
    await expect(
      registry.connect(stranger).removeAuthorizedSubmitter(owner.address)
    ).to.be.revertedWithCustomError(registry, "OwnableUnauthorizedAccount");
  });

});
