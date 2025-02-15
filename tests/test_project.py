from devtools import debug


PREFIX = "/api/v1/project"


async def test_project_get(client, db, project_factory, MockCurrentUser):
    # unauthenticated

    res = await client.get(f"{PREFIX}/")
    assert res.status_code == 401

    # authenticated
    async with MockCurrentUser(persist=True) as user:
        other_project = await project_factory(user)

    async with MockCurrentUser(persist=True) as user:
        res = await client.get(f"{PREFIX}/")
        debug(res)
        assert res.status_code == 200
        assert res.json() == []

        await project_factory(user)
        res = await client.get(f"{PREFIX}/")
        data = res.json()
        debug(data)
        assert res.status_code == 200
        assert len(data) == 1

        project_id = data[0]["id"]
        res = await client.get(f"{PREFIX}/{project_id}")
        assert res.status_code == 200
        assert res.json()["id"] == project_id

        # fail on non existent project
        res = await client.get(f"{PREFIX}/666")
        assert res.status_code == 404

        # fail on other owner's project
        res = await client.get(f"{PREFIX}/{other_project.id}")
        assert res.status_code == 403


async def test_project_creation(app, client, MockCurrentUser, db):
    payload = dict(
        name="new project",
        project_dir="/some/path/",
    )
    res = await client.post(f"{PREFIX}/", json=payload)
    data = res.json()
    assert res.status_code == 401

    async with MockCurrentUser(persist=True):
        res = await client.post(f"{PREFIX}/", json=payload)
        data = res.json()
        assert res.status_code == 201
        debug(data)
        assert data["name"] == payload["name"]
        assert data["project_dir"] == payload["project_dir"]


async def test_project_creation_name_constraint(
    app, client, MockCurrentUser, db
):
    payload = dict(
        name="new project",
        project_dir="/some/path/",
    )
    res = await client.post(f"{PREFIX}/", json=payload)
    assert res.status_code == 401

    async with MockCurrentUser(persist=True):

        # Create a first project named "new project"
        res = await client.post(f"{PREFIX}/", json=payload)
        assert res.status_code == 201

        # Create a second project named "new project", and check that this
        # fails with 422_UNPROCESSABLE_ENTITY
        res = await client.post(f"{PREFIX}/", json=payload)
        assert res.status_code == 422


async def test_add_dataset(app, client, MockCurrentUser, db):

    async with MockCurrentUser(persist=True):

        # CREATE A PROJECT

        res = await client.post(
            f"{PREFIX}/",
            json=dict(
                name="test project",
                project_dir="/tmp/",
            ),
        )
        assert res.status_code == 201
        project = res.json()
        project_id = project["id"]

        # ADD DATASET

        payload = dict(
            name="new dataset",
            project_id=project_id,
            meta={"xy": 2},
        )
        res = await client.post(
            f"{PREFIX}/{project_id}/",
            json=payload,
        )
        assert res.status_code == 201
        dataset = res.json()
        assert dataset["name"] == payload["name"]
        assert dataset["project_id"] == payload["project_id"]
        assert dataset["meta"] == payload["meta"]

        # EDIT DATASET

        payload = dict(name="new dataset name", meta={})
        res = await client.patch(
            f"{PREFIX}/{project_id}/{dataset['id']}",
            json=payload,
        )
        patched_dataset = res.json()
        debug(patched_dataset)
        assert res.status_code == 200
        for k, v in payload.items():
            assert patched_dataset[k] == payload[k]

        # ADD RESOURCE TO DATASET

        payload = dict(path="/some/absolute/path", glob_pattern="*.png")
        res = await client.post(
            f"{PREFIX}/{project_id}/{dataset['id']}",
            json=payload,
        )
        assert res.status_code == 201
        resource = res.json()
        debug(resource)
        assert resource["path"] == payload["path"]


async def test_add_dataset_local_path_error(app, client, MockCurrentUser, db):

    async with MockCurrentUser(persist=True):

        # CREATE A PROJECT

        res = await client.post(
            f"{PREFIX}/",
            json=dict(
                name="test project",
                project_dir="/tmp/",
            ),
        )
        assert res.status_code == 201
        project = res.json()
        project_id = project["id"]

        # ADD DATASET

        payload = dict(
            name="new dataset",
            project_id=project_id,
            meta={"xy": 2},
        )
        res = await client.post(
            f"{PREFIX}/{project_id}/",
            json=payload,
        )
        assert res.status_code == 201
        dataset = res.json()
        assert dataset["name"] == payload["name"]
        assert dataset["project_id"] == payload["project_id"]
        assert dataset["meta"] == payload["meta"]

        # EDIT DATASET

        payload = dict(name="new dataset name", meta={})
        res = await client.patch(
            f"{PREFIX}/{project_id}/{dataset['id']}",
            json=payload,
        )
        patched_dataset = res.json()
        debug(patched_dataset)
        assert res.status_code == 200
        for k, v in payload.items():
            assert patched_dataset[k] == payload[k]

        # ADD WRONG RESOURCE TO DATASET

        payload = dict(path="some/local/path", glob_pattern="*.png")
        debug(payload["path"])

        res = await client.post(
            f"{PREFIX}/{project_id}/{dataset['id']}",
            json=payload,
        )
        assert res.status_code == 422


async def test_delete_project(client, MockCurrentUser):

    async with MockCurrentUser(persist=True):
        res = await client.get(f"{PREFIX}/")
        data = res.json()
        assert len(data) == 0

        # CREATE A PRJ
        res = await client.post(
            f"{PREFIX}/", json=dict(name="name", project_dir="project dir")
        )
        p = res.json()

        res = await client.get(f"{PREFIX}/")
        data = res.json()
        debug(data)

        assert res.status_code == 200
        assert len(data) == 1

        # DELETE PRJ
        res = await client.delete(f"{PREFIX}/{p['id']}")
        assert res.status_code == 204

        # GET LIST again and check that it is empty
        res = await client.get(f"{PREFIX}/")
        data = res.json()
        assert len(data) == 0


async def test_edit_resource(
    client, MockCurrentUser, project_factory, dataset_factory, resource_factory
):
    async with MockCurrentUser(persist=True) as user:
        prj = await project_factory(user)
        ds = await dataset_factory(project=prj)
        orig_resource = await resource_factory(dataset=ds)

        payload = dict(path="my/new/path")
        res = await client.patch(
            f"{PREFIX}/{prj.id}/{ds.id}/{orig_resource.id}", json=payload
        )
        data = res.json()
        debug(data)
        assert res.status_code == 200
        for key, value in payload.items():
            assert data[key] == value

        for key, value in orig_resource.dict().items():
            if key not in payload:
                assert data[key] == value


async def test_delete_dataset(
    client, MockCurrentUser, project_factory, dataset_factory
):
    async with MockCurrentUser(persist=True) as user:
        prj = await project_factory(user)
        ds0 = await dataset_factory(project=prj)
        ds1 = await dataset_factory(project=prj)

        ds_ids = (ds0.id, ds1.id)

        res = await client.get(f"{PREFIX}/{prj.id}")
        prj_dict = res.json()
        assert len(prj_dict["dataset_list"]) == 2
        assert prj_dict["dataset_list"][0]["id"] in ds_ids
        assert prj_dict["dataset_list"][1]["id"] in ds_ids

        res = await client.delete(f"{PREFIX}/{prj.id}/{ds0.id}")
        assert res.status_code == 204

        res = await client.get(f"{PREFIX}/{prj.id}")
        prj_dict = res.json()
        assert len(prj_dict["dataset_list"]) == 1
        assert prj_dict["dataset_list"][0]["id"] == ds1.id
