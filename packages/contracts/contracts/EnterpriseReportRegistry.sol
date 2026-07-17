// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title EnterpriseReportRegistry
/// @notice Anchors immutable proof that an AgentOps Cloud Executive Report
///         existed, unmodified, at a point in time.
/// @dev Only a cryptographic hash and small metadata are ever stored here.
///      Report contents, org data, agent data, and customer information are
///      never written on-chain — see docs/ContractArchitecture.md for why.
///      A report is identified by its own hash (`sha256` of the canonical
///      JSON serialization computed off-chain), so registering the same
///      hash twice is rejected outright: it doubles as tamper/replay
///      protection without any extra bookkeeping.
contract EnterpriseReportRegistry is Ownable {
    /// @notice On-chain record for a single registered report hash.
    /// @param workspaceId Opaque workspace/org identifier (never a name or PII).
    /// @param timestamp Block timestamp at registration.
    /// @param version Product version string that produced the report (see AgentOpsRegistry).
    /// @param metadataURI Optional pointer (e.g. to an off-chain audit log) — empty string if unused.
    /// @param submitter Address that submitted the proof.
    struct ReportProof {
        string workspaceId;
        uint256 timestamp;
        string version;
        string metadataURI;
        address submitter;
    }

    /// @dev reportHash => proof. Absence is represented by `timestamp == 0`.
    mapping(bytes32 => ReportProof) private _proofs;

    /// @notice Addresses allowed to call `registerReport`, independent of
    ///         contract ownership — lets the backend's signer key rotate or
    ///         differ from the deployer/owner key without redeploying.
    mapping(address => bool) public authorizedSubmitters;

    event ReportRegistered(
        bytes32 indexed reportHash,
        string workspaceId,
        uint256 timestamp,
        string version,
        address indexed submitter
    );
    event SubmitterAuthorized(address indexed submitter);
    event SubmitterRevoked(address indexed submitter);

    error ReportAlreadyRegistered(bytes32 reportHash);
    error NotAuthorized(address caller);

    modifier onlyAuthorized() {
        if (!authorizedSubmitters[msg.sender]) revert NotAuthorized(msg.sender);
        _;
    }

    constructor(address initialOwner) Ownable(initialOwner) {
        authorizedSubmitters[initialOwner] = true;
        emit SubmitterAuthorized(initialOwner);
    }

    /// @notice Registers proof that a report with `reportHash` existed at this block.
    /// @dev Reverts if `reportHash` was already registered — a report hash
    ///      is only ever written once, which is what makes later comparison
    ///      meaningful (see `verifyReport`).
    /// @param reportHash sha256 hash of the canonical report serialization, computed off-chain.
    /// @param workspaceId Opaque workspace/org identifier.
    /// @param version Product version string (see AgentOpsRegistry.currentVersion).
    /// @param metadataURI Optional off-chain pointer; pass "" if unused.
    function registerReport(
        bytes32 reportHash,
        string calldata workspaceId,
        string calldata version,
        string calldata metadataURI
    ) external onlyAuthorized {
        if (_proofs[reportHash].timestamp != 0) revert ReportAlreadyRegistered(reportHash);

        _proofs[reportHash] = ReportProof({
            workspaceId: workspaceId,
            timestamp: block.timestamp,
            version: version,
            metadataURI: metadataURI,
            submitter: msg.sender
        });

        emit ReportRegistered(reportHash, workspaceId, block.timestamp, version, msg.sender);
    }

    /// @notice Looks up a previously registered report hash.
    /// @param reportHash The hash to verify.
    /// @return exists Whether this hash was ever registered.
    /// @return proof The stored proof (zero-valued if `exists` is false).
    function verifyReport(bytes32 reportHash) external view returns (bool exists, ReportProof memory proof) {
        proof = _proofs[reportHash];
        exists = proof.timestamp != 0;
    }

    /// @notice Grants an address permission to call `registerReport`.
    function addAuthorizedSubmitter(address submitter) external onlyOwner {
        authorizedSubmitters[submitter] = true;
        emit SubmitterAuthorized(submitter);
    }

    /// @notice Revokes an address's permission to call `registerReport`.
    function removeAuthorizedSubmitter(address submitter) external onlyOwner {
        authorizedSubmitters[submitter] = false;
        emit SubmitterRevoked(submitter);
    }
}
