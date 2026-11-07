# RDD2022 dataset inspection

Generated: 2026-11-04T20:25:11Z  
Root: `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022`  
Elapsed: 1357.5 s  
Near-duplicate settings: dHash 64 bits, Hamming <= 3, max bucket 500

## Totals

| Metric | Value |
| :--- | ---: |
| images | 47,420 |
| annotations_parsed | 38,385 |
| annotations_found | 38,385 |
| objects | 65,712 |
| images_with_annotation | 38,385 |
| images_without_annotation | 9,035 |
| annotations_without_image | 0 |
| unreadable_images | 0 |
| malformed_xml | 0 |
| images_without_objects | 11,724 |
| objects_without_name | 0 |
| xml_size_missing | 0 |
| xml_size_unparsable | 0 |
| xml_size_mismatch | 0 |
| total_image_bytes | 13,807,757,095 |
| total_xml_bytes | 24,718,784 |
| total_bytes | 13,832,475,879 |

## Images and annotations per country and split

| Country | Split | Images | Annotations | Objects | Classes |
| :--- | :--- | ---: | ---: | ---: | :--- |
| China_Drone | train | 2,401 | 2,401 | 3,840 | Block crack=3, D00=1426, D10=1263, D20=293, D40=86, Repair=769 |
| China_MotorBike | test | 500 | 0 | 0 | - |
| China_MotorBike | train | 1,977 | 1,977 | 4,927 | D00=2678, D10=1096, D20=641, D40=235, Repair=277 |
| Czech | test | 709 | 0 | 0 | - |
| Czech | train | 2,829 | 2,829 | 1,745 | D00=988, D10=399, D20=161, D40=197 |
| India | test | 1,959 | 0 | 0 | - |
| India | train | 7,706 | 7,706 | 8,203 | D00=1555, D01=179, D0w0=1, D10=68, D11=45, D20=2021, D40=3187, D43=57, D44=1062, D50=28 |
| Japan | test | 2,627 | 0 | 0 | - |
| Japan | train | 10,506 | 10,506 | 24,754 | D00=4049, D10=3979, D20=6199, D40=2243, D43=736, D44=3995, D50=3553 |
| Norway | test | 2,040 | 0 | 0 | - |
| Norway | train | 8,161 | 8,161 | 11,229 | D00=8570, D10=1730, D20=468, D40=461 |
| United_States | test | 1,200 | 0 | 0 | - |
| United_States | train | 4,805 | 4,805 | 11,014 | D00=6750, D10=3295, D20=834, D40=135 |

## Class distribution

| Code | Objects | Images | Countries | In scope |
| :--- | ---: | ---: | :--- | :--- |
| Block crack | 3 | 3 | China_Drone | False |
| D00 | 26,016 | 13,548 | China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States | True |
| D01 | 179 | 118 | India | False |
| D0w0 | 1 | 1 | India | False |
| D10 | 11,830 | 7,709 | China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States | True |
| D11 | 45 | 36 | India | False |
| D20 | 10,617 | 8,412 | China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States | True |
| D40 | 6,544 | 3,674 | China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States | True |
| D43 | 793 | 753 | India, Japan | False |
| D44 | 5,057 | 4,079 | India, Japan | False |
| D50 | 3,581 | 2,638 | India, Japan | False |
| Repair | 1,046 | 803 | China_Drone, China_MotorBike | False |

Codes outside the RoadVision four: Block crack, D01, D0w0, D11, D43, D44, D50, Repair

## Image properties

| Property | Value |
| :--- | :--- |
| Extensions | {'.jpg': 47420} |
| Width min/max/mean/median | {'min': 512, 'max': 4040, 'mean': 1322.6, 'median': 640.0} |
| Height min/max/mean/median | {'min': 512, 'max': 2044, 'mean': 932.0, 'median': 640.0} |
| Top dimensions | [('600x600', 16268), ('720x720', 9665), ('640x640', 6005), ('4040x2035', 5400), ('512x512', 4878), ('3643x2041', 3655), ('3650x2044', 1146), ('1024x1024', 191), ('540x540', 152), ('1080x1080', 60)] |

## XML structure

Root tags: `{'annotation': 38385}`  
First-sample child tags: `{'folder': 38385, 'filename': 38385, 'size': 38385, 'segmented': 31698, 'object': 65712}`

## Duplicates

| Check | Result |
| :--- | ---: |
| Exact duplicate groups (SHA-256) | 2 |
| Extra copies beyond the first | 2 |
| Near-duplicate groups (dHash) | 635 |
| Images in near-duplicate groups | 2,395 |
| Near-duplicate pair edges | 7,673 |
| Largest near-duplicate group | 358 |
| Skipped buckets (too large) | 3 |
| Images in skipped buckets | 2,077 |
| Duplicate file names | 0 |

## Problems

- Unreadable images: **0**
- Malformed XML: **0**
- Images without annotation: **9,035**
- Annotations without image: **0**
- XML images with zero objects: **11,724**
- Objects without a class name: **0**
- XML size element missing: **0**
- XML size unparsable: **0**
- XML size vs real image mismatch: **0**

### Images without annotation (first entries)

- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001977.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001978.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001979.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001980.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001981.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001982.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001983.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001984.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001985.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001986.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001987.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001988.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001989.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001990.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001991.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001992.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001993.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001994.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001995.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001996.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001997.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001998.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_001999.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002000.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002001.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002002.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002003.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002004.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002005.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002006.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002007.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002008.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002009.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002010.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002011.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002012.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002013.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002014.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002015.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002016.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002017.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002018.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002019.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002020.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002021.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002022.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002023.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002024.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002025.jpg`
- `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022\China_MotorBike\test\images\China_MotorBike_002026.jpg`

## PRD v1.1 Table 7 fields available at this stage

| Field | Value from this inspection |
| :--- | :--- |
| Images downloaded | 47,420 |
| Images with an annotation file | 38,385 |
| Objects across all annotations | 65,712 |
| Exclusions and reasons | not applicable yet: nothing was converted or excluded |
| Training / validation / test counts | not applicable yet: no split was created |
| Class distribution per split | not applicable yet: no split was created |
| Subset size and selection | not applicable yet: no training |
| Random seed and split file | not applicable yet |
| Leakage check | exact + dHash duplicate counts reported above; split-level check deferred |
