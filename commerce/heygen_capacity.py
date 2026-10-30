"""Offline capacity estimates; never connects to HeyGen, a bank, or a database.

The request count assumes perfectly packed 4,000-code-point chunks. Actual
chapter/segment boundaries, latency tails and interruptions can only add work.
"""
import argparse
import json
import math


def estimate(characters, books=1, *, rpm=25, chunk=4000, concurrency=6,
             latency_seconds=10, retry_ratio=0):
    for value in (characters, books, chunk, concurrency):
        if type(value) is not int or value < 1:
            raise ValueError('Counts must be positive integers')
    if not 0 < rpm <= 30 or not 0 < chunk <= 5000:
        raise ValueError('Provider bounds are 30 requests/minute and 5000 characters/request')
    if not math.isfinite(latency_seconds) or latency_seconds <= 0:
        raise ValueError('A positive finite latency is required')
    if not math.isfinite(retry_ratio) or retry_ratio < 0:
        raise ValueError('Retry overhead must be finite and non-negative')
    requests_per_book=math.ceil(characters/chunk)
    requests=requests_per_book*books
    effective_rpm=min(rpm,60*concurrency/latency_seconds)
    return dict(charactersPerBook=characters,books=books,
        idealRequestsPerBook=requests_per_book,idealRequests=requests,
        requestBudgetRPM=rpm,latencySeconds=latency_seconds,concurrency=concurrency,
        effectiveAttemptRPM=round(effective_rpm,4),retryOverheadRatio=retry_ratio,
        workBudgetMinutes=round(requests*(1+retry_ratio)/effective_rpm,4),
        estimatedAudioHoursPerBook=round(characters/900/60,4),
        caveat='Optimistic steady-state work budget; excludes final request latency, packing losses, outages and downloads. Not a completion SLA.')


def report():
    return dict(policy=dict(trialsPerMac=10,charactersPerTrial=5000,
                    maxTrialCharactersPerMac=50000,providerRPM=30,plannedRPM=25),
        books=[estimate(n) for n in (4000,27000,54000,108000,216000,300000)],
        freeCampaign=[dict(users=users,attemptsPerUser=attempts,
            **estimate(5000,users*attempts)) for users in (10,100,1000) for attempts in (1,10)],
        paidBatch=[estimate(216000,n,rpm=20) for n in (1,10,100)],
        latencySensitivity=[estimate(216000,latency_seconds=n,retry_ratio=.1)
            for n in (10,20,30)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--characters',type=int)
    parser.add_argument('--books',type=int,default=1)
    parser.add_argument('--rpm',type=float,default=25)
    parser.add_argument('--concurrency',type=int,default=6)
    parser.add_argument('--latency-seconds',type=float,default=10)
    parser.add_argument('--retry-ratio',type=float,default=0)
    args=parser.parse_args()
    result=report() if args.characters is None else estimate(args.characters,args.books,
        rpm=args.rpm,concurrency=args.concurrency,latency_seconds=args.latency_seconds,
        retry_ratio=args.retry_ratio)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
