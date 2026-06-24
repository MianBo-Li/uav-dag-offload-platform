from json import dumps

from app.services.dead_letter_flow_verifier import RabbitMQDeadLetterFlowVerifier


def main() -> int:
    result = RabbitMQDeadLetterFlowVerifier().verify_probe_flow()
    print(
        dumps(
            {
                "probe_id": result.probe_id,
                "probe_queue": result.probe_queue,
                "probe_routing_key": result.probe_routing_key,
                "main_queue_dead_letter_configured": result.main_queue_dead_letter_configured,
                "published": result.published,
                "rejected": result.rejected,
                "found_in_dlq": result.found_in_dlq,
                "dlq_message_count": result.dlq_message_count,
                "error_message": result.error_message,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if (
        result.main_queue_dead_letter_configured
        and result.published
        and result.rejected
        and result.found_in_dlq
    ):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
