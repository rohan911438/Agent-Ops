import { expect } from "chai";
import { ethers } from "hardhat";
import { ServicePricing } from "../typechain-types";

describe("ServicePricing", () => {
  let pricing: ServicePricing;
  let owner: any;
  let stranger: any;

  beforeEach(async () => {
    [owner, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ServicePricing");
    pricing = (await Factory.deploy(owner.address)) as unknown as ServicePricing;
    await pricing.waitForDeployment();
  });

  it("registers a service at price 0 and emits ServiceRegistered", async () => {
    await expect(pricing.connect(owner).registerService("health_scan", "Health Scan", 0, "USD"))
      .to.emit(pricing, "ServiceRegistered")
      .withArgs("health_scan", "Health Scan", 0, "USD");

    const service = await pricing.getService("health_scan");
    expect(service.name).to.equal("Health Scan");
    expect(service.price).to.equal(0);
    expect(service.currency).to.equal("USD");
    expect(service.enabled).to.equal(true);
    expect(service.version).to.equal(1);

    expect(await pricing.serviceCount()).to.equal(1);
    expect(await pricing.serviceIds(0)).to.equal("health_scan");
  });

  it("reverts on duplicate service registration", async () => {
    await pricing.connect(owner).registerService("health_scan", "Health Scan", 0, "USD");
    await expect(
      pricing.connect(owner).registerService("health_scan", "Health Scan", 0, "USD")
    ).to.be.revertedWithCustomError(pricing, "ServiceAlreadyRegistered");
  });

  it("updates price, bumps version, and emits PriceUpdated with old/new price", async () => {
    await pricing.connect(owner).registerService("executive_report", "Executive Report", 0, "USD");

    await expect(pricing.connect(owner).updatePrice("executive_report", 1500))
      .to.emit(pricing, "PriceUpdated")
      .withArgs("executive_report", 0, 1500);

    const service = await pricing.getService("executive_report");
    expect(service.price).to.equal(1500);
    expect(service.version).to.equal(2);
  });

  it("toggles enabled state and emits ServiceEnabledUpdated", async () => {
    await pricing.connect(owner).registerService("optimization_planner", "Optimization Planner", 0, "USD");

    await expect(pricing.connect(owner).setEnabled("optimization_planner", false))
      .to.emit(pricing, "ServiceEnabledUpdated")
      .withArgs("optimization_planner", false);

    expect((await pricing.getService("optimization_planner")).enabled).to.equal(false);
  });

  it("reverts updatePrice/setEnabled/getService for an unregistered service", async () => {
    await expect(pricing.updatePrice("unknown", 100)).to.be.revertedWithCustomError(pricing, "ServiceNotFound");
    await expect(pricing.setEnabled("unknown", true)).to.be.revertedWithCustomError(pricing, "ServiceNotFound");
    await expect(pricing.getService("unknown")).to.be.revertedWithCustomError(pricing, "ServiceNotFound");
  });

  it("rejects registerService/updatePrice/setEnabled from a non-owner", async () => {
    await expect(
      pricing.connect(stranger).registerService("health_scan", "Health Scan", 0, "USD")
    ).to.be.revertedWithCustomError(pricing, "OwnableUnauthorizedAccount");

    await pricing.connect(owner).registerService("health_scan", "Health Scan", 0, "USD");

    await expect(pricing.connect(stranger).updatePrice("health_scan", 500)).to.be.revertedWithCustomError(
      pricing,
      "OwnableUnauthorizedAccount"
    );
    await expect(pricing.connect(stranger).setEnabled("health_scan", false)).to.be.revertedWithCustomError(
      pricing,
      "OwnableUnauthorizedAccount"
    );
  });
});
