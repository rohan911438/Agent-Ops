// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title AgentOpsRegistry
/// @notice Registers AgentOps Cloud product releases (backend, frontend,
///         and contract versions bundled together) so an enterprise
///         customer can verify exactly which product version produced a
///         given Executive Report.
contract AgentOpsRegistry is Ownable {
    /// @param deploymentTimestamp Block timestamp at registration.
    /// @param backendVersion apps/api release identifier.
    /// @param frontendVersion apps/web release identifier.
    /// @param contractVersion This contract suite's release identifier.
    struct ProductVersion {
        uint256 deploymentTimestamp;
        string backendVersion;
        string frontendVersion;
        string contractVersion;
    }

    /// @dev version label => ProductVersion. Absence is `deploymentTimestamp == 0`.
    mapping(string => ProductVersion) private _versions;

    /// @notice All registered version labels, in registration order.
    string[] public versionHistory;

    /// @notice The most recently registered version label.
    string public currentVersion;

    event VersionRegistered(
        string version,
        uint256 timestamp,
        string backendVersion,
        string frontendVersion,
        string contractVersion
    );

    error VersionAlreadyRegistered(string version);
    error VersionNotFound(string version);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Registers a new product release.
    function registerVersion(
        string calldata version,
        string calldata backendVersion,
        string calldata frontendVersion,
        string calldata contractVersion
    ) external onlyOwner {
        if (_versions[version].deploymentTimestamp != 0) revert VersionAlreadyRegistered(version);

        _versions[version] = ProductVersion({
            deploymentTimestamp: block.timestamp,
            backendVersion: backendVersion,
            frontendVersion: frontendVersion,
            contractVersion: contractVersion
        });
        versionHistory.push(version);
        currentVersion = version;

        emit VersionRegistered(version, block.timestamp, backendVersion, frontendVersion, contractVersion);
    }

    /// @notice Reads the most recently registered product version.
    function getCurrentVersion() external view returns (ProductVersion memory) {
        return _versions[currentVersion];
    }

    /// @notice Reads a specific registered product version.
    function getVersion(string calldata version) external view returns (ProductVersion memory) {
        ProductVersion memory productVersion = _versions[version];
        if (productVersion.deploymentTimestamp == 0) revert VersionNotFound(version);
        return productVersion;
    }

    /// @notice Number of registered versions — paired with `versionHistory` for enumeration.
    function versionCount() external view returns (uint256) {
        return versionHistory.length;
    }
}
