import { expect } from "chai";
import { ethers } from "hardhat";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";
import { AgentOpsRegistry } from "../typechain-types";

describe("AgentOpsRegistry", () => {
  let registry: AgentOpsRegistry;
  let owner: any;
  let stranger: any;

  beforeEach(async () => {
    [owner, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("AgentOpsRegistry");
    registry = (await Factory.deploy(owner.address)) as unknown as AgentOpsRegistry;
    await registry.waitForDeployment();
  });

  it("registers a version, sets currentVersion, and emits VersionRegistered", async () => {
    await expect(registry.connect(owner).registerVersion("phase4.0.0", "api-1.4.0", "web-1.4.0", "contracts-1.0.0"))
      .to.emit(registry, "VersionRegistered")
      .withArgs("phase4.0.0", anyValue, "api-1.4.0", "web-1.4.0", "contracts-1.0.0");

    expect(await registry.currentVersion()).to.equal("phase4.0.0");
    expect(await registry.versionCount()).to.equal(1);
    expect(await registry.versionHistory(0)).to.equal("phase4.0.0");

    const current = await registry.getCurrentVersion();
    expect(current.backendVersion).to.equal("api-1.4.0");
    expect(current.frontendVersion).to.equal("web-1.4.0");
    expect(current.contractVersion).to.equal("contracts-1.0.0");
    expect(current.deploymentTimestamp).to.be.greaterThan(0);
  });

  it("advances currentVersion on each subsequent registration", async () => {
    await registry.connect(owner).registerVersion("phase4.0.0", "api-1.4.0", "web-1.4.0", "contracts-1.0.0");
    await registry.connect(owner).registerVersion("phase4.1.0", "api-1.4.1", "web-1.4.1", "contracts-1.0.0");

    expect(await registry.currentVersion()).to.equal("phase4.1.0");
    expect(await registry.versionCount()).to.equal(2);

    const older = await registry.getVersion("phase4.0.0");
    expect(older.backendVersion).to.equal("api-1.4.0");
  });

  it("reverts on duplicate version registration", async () => {
    await registry.connect(owner).registerVersion("phase4.0.0", "api-1.4.0", "web-1.4.0", "contracts-1.0.0");
    await expect(
      registry.connect(owner).registerVersion("phase4.0.0", "api-1.4.0", "web-1.4.0", "contracts-1.0.0")
    ).to.be.revertedWithCustomError(registry, "VersionAlreadyRegistered");
  });

  it("reverts getVersion for an unregistered version", async () => {
    await expect(registry.getVersion("nope")).to.be.revertedWithCustomError(registry, "VersionNotFound");
  });

  it("rejects registerVersion from a non-owner", async () => {
    await expect(
      registry.connect(stranger).registerVersion("phase4.0.0", "api-1.4.0", "web-1.4.0", "contracts-1.0.0")
    ).to.be.revertedWithCustomError(registry, "OwnableUnauthorizedAccount");
  });
});
