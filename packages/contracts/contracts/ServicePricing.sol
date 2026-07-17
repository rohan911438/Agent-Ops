// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ServicePricing
/// @notice Pricing metadata for AgentOps Cloud services. Every service is
///         priced at 0 today (the product is free) — this contract exists
///         so a future price change is a config update (owner calls
///         `updatePrice`), never a redeployment or an API contract change.
/// @dev No payment logic lives here. This is metadata only — see
///      docs/FutureMonetization.md for how a payment provider (e.g. x402)
///      would eventually read these values before charging anything.
contract ServicePricing is Ownable {
    /// @param name Human-readable service name.
    /// @param price Price in the smallest unit of `currency` (0 = free).
    /// @param currency Currency code, e.g. "USD".
    /// @param enabled Whether the service is currently offered.
    /// @param version Bumped whenever pricing terms materially change.
    struct Service {
        string name;
        uint256 price;
        string currency;
        bool enabled;
        uint256 version;
    }

    /// @dev serviceId => Service. Absence is represented by `version == 0`.
    mapping(string => Service) private _services;

    /// @notice All registered service ids, in registration order.
    string[] public serviceIds;

    event ServiceRegistered(string indexed serviceId, string name, uint256 price, string currency);
    event PriceUpdated(string indexed serviceId, uint256 oldPrice, uint256 newPrice);
    event ServiceEnabledUpdated(string indexed serviceId, bool enabled);

    error ServiceAlreadyRegistered(string serviceId);
    error ServiceNotFound(string serviceId);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Registers a new service and its initial price.
    function registerService(
        string calldata serviceId,
        string calldata name,
        uint256 price,
        string calldata currency
    ) external onlyOwner {
        if (_services[serviceId].version != 0) revert ServiceAlreadyRegistered(serviceId);

        _services[serviceId] = Service({name: name, price: price, currency: currency, enabled: true, version: 1});
        serviceIds.push(serviceId);

        emit ServiceRegistered(serviceId, name, price, currency);
    }

    /// @notice Updates the price of an existing service. Enterprise plans
    ///         are free today; this is how that changes later without a
    ///         redeployment or a backend/API change.
    function updatePrice(string calldata serviceId, uint256 newPrice) external onlyOwner {
        Service storage service = _services[serviceId];
        if (service.version == 0) revert ServiceNotFound(serviceId);

        uint256 oldPrice = service.price;
        service.price = newPrice;
        service.version += 1;

        emit PriceUpdated(serviceId, oldPrice, newPrice);
    }

    /// @notice Enables or disables a service without deleting its pricing history.
    function setEnabled(string calldata serviceId, bool enabled) external onlyOwner {
        Service storage service = _services[serviceId];
        if (service.version == 0) revert ServiceNotFound(serviceId);

        service.enabled = enabled;
        emit ServiceEnabledUpdated(serviceId, enabled);
    }

    /// @notice Reads a service's current pricing metadata.
    function getService(string calldata serviceId) external view returns (Service memory) {
        Service memory service = _services[serviceId];
        if (service.version == 0) revert ServiceNotFound(serviceId);
        return service;
    }

    /// @notice Number of registered services — paired with `serviceIds` for enumeration.
    function serviceCount() external view returns (uint256) {
        return serviceIds.length;
    }
}
